import httpx
import os
import logging
import json
from typing import AsyncIterator, Union, Dict, Any
from pydantic import ValidationError
from async_sse_client import EventSource

from models import DeepSearchInput, DeepSearchResponse, DeepSearchChunk

logger = logging.getLogger(__name__)

class JinaDeepSearchClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai/v1"
    DEFAULT_TIMEOUT = 180.0  # Seconds, increased for potentially long searches

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        """
        Initializes the JinaDeepSearchClient.

        Args:
            api_key: The Jina API key. Reads from JINA_API_KEY env var if None.
            base_url: The base URL for the Jina API. Defaults to https://deepsearch.jina.ai/v1.
            timeout: Default request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key not provided or found in JINA_API_KEY environment variable.")

        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json", # For non-streaming
            "X-DeepSearch-Client": "mcp-server/0.1.0" # Optional client identifier
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[httpx.Response, EventSource]:
        """Internal method to make HTTP requests."""
        try:
            headers = self.headers.copy()
            if stream:
                headers["Accept"] = "text/event-stream"

            if stream:
                # For streaming, httpx doesn't handle SSE directly well with POST
                # We use async_sse_client which needs the request object
                req = self.client.build_request(
                    method=method,
                    url=endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                # Note: async_sse_client doesn't automatically raise for status on connection
                # Error handling needs to be done during iteration
                return EventSource(req, client=self.client)
            else:
                response = await self.client.request(
                    method=method,
                    url=endpoint,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
                return response

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.timeout}s: {e}")
            raise TimeoutError(f"API request timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"Network or request error: {e}")
            raise ConnectionError(f"API request failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            # You might want to raise a more specific custom exception here
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during the API request: {e}")
            raise

    async def chat_completion(
        self, params: DeepSearchInput
    ) -> Union[DeepSearchResponse, AsyncIterator[DeepSearchChunk]]:
        """
        Performs a deep search chat completion.

        Args:
            params: Input parameters conforming to the DeepSearchInput model.

        Returns:
            If stream=False, returns a DeepSearchResponse object.
            If stream=True, returns an async iterator yielding DeepSearchChunk objects.

        Raises:
            ValueError: If input validation fails.
            ConnectionError: If there's a network issue.
            TimeoutError: If the request times out.
            httpx.HTTPStatusError: For API-level errors (4xx, 5xx).
            Exception: For other unexpected errors.
        """
        endpoint = "/chat/completions"
        payload = params.model_dump(exclude_none=True) # Use exclude_none from model config

        if params.stream:
            return self._stream_chat_completion(endpoint, payload)
        else:
            return await self._non_stream_chat_completion(endpoint, payload)

    async def _non_stream_chat_completion(self, endpoint: str, payload: Dict[str, Any]) -> DeepSearchResponse:
        """Handles non-streaming chat completion requests."""
        response = await self._request("POST", endpoint, payload=payload, stream=False)
        try:
            response_data = response.json()
            return DeepSearchResponse.model_validate(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {response.text}")
            raise ValueError(f"Invalid JSON received from API: {e}") from e
        except ValidationError as e:
            logger.error(f"Failed to validate API response: {response_data}")
            raise ValueError(f"API response validation failed: {e}") from e

    async def _stream_chat_completion(self, endpoint: str, payload: Dict[str, Any]) -> AsyncIterator[DeepSearchChunk]:
        """Handles streaming chat completion requests using SSE."""
        event_source = await self._request("POST", endpoint, payload=payload, stream=True)
        try:
            async with event_source as source:
                async for event in source:
                    if event.event == 'error':
                        logger.error(f"SSE Error event received: {event.data}")
                        # Attempt to parse error details if JSON
                        try:
                            error_data = json.loads(event.data)
                            raise httpx.HTTPStatusError(
                                message=error_data.get('message', event.data),
                                request=event_source.request,
                                response=httpx.Response(status_code=error_data.get('status', 500), json=error_data)
                            )
                        except json.JSONDecodeError:
                            raise ConnectionError(f"Received non-JSON SSE error: {event.data}")
                    elif event.event == 'message' or event.type == 'message': # Check both event and type
                        if event.data.strip() == '[DONE]':
                            logger.info("SSE stream finished with [DONE] message.")
                            break
                        try:
                            chunk_data = json.loads(event.data)
                            yield DeepSearchChunk.model_validate(chunk_data)
                        except json.JSONDecodeError:
                            logger.warning(f"Received non-JSON SSE data: {event.data}")
                            continue # Skip malformed data
                        except ValidationError as e:
                            logger.warning(f"Failed to validate SSE chunk: {event.data}, Error: {e}")
                            continue # Skip invalid chunks
                    else:
                        logger.debug(f"Received unhandled SSE event type '{event.event}' or type '{event.type}': {event.data}")

        except httpx.HTTPStatusError as e:
            # Errors during connection or initial response might raise this
            logger.error(f"HTTP error during SSE connection: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.TransportError as e:
            # Handles connection errors, read timeouts during stream etc.
            logger.error(f"Transport error during SSE stream: {e}")
            raise ConnectionError(f"SSE stream transport error: {e}") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred during SSE processing: {e}")
            raise
        finally:
            # Ensure the underlying client connection is closed if EventSource didn't close it
            # This might be handled internally by async_sse_client's context manager
            pass

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
