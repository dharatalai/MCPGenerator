import httpx
import logging
import os
import json
from typing import Dict, Any, Union, AsyncGenerator, Optional
from pydantic import ValidationError

from models import DeepSearchChatInput, DeepSearchChatOutput, DeepSearchChatChunk

logger = logging.getLogger(__name__)

class DeepSearchError(Exception):
    """Custom exception for DeepSearch API errors."""
    def __init__(self, status_code: Optional[int] = None, message: str = "DeepSearch API error"):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

class DeepSearchClient:
    """Asynchronous client for interacting with the Jina DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 180.0):
        """
        Initializes the DeepSearchClient.

        Args:
            api_key: The Jina API key. Reads from JINA_API_KEY env var if not provided.
            base_url: The base URL for the DeepSearch API. Reads from DEEPSEARCH_API_BASE_URL or defaults.
            timeout: Default timeout for HTTP requests in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key not provided or found in JINA_API_KEY environment variable.")

        self.base_url = base_url or os.getenv("DEEPSEARCH_API_BASE_URL", "https://deepsearch.jina.ai")
        self.endpoint = "/v1/chat/completions"
        self.timeout = timeout

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # For non-streaming
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """Makes an asynchronous request to the DeepSearch API."""
        request_headers = self.headers.copy()
        if stream:
            request_headers["Accept"] = "text/event-stream"

        try:
            if stream:
                return self._stream_request(method, endpoint, payload, request_headers)
            else:
                response = await self.client.request(method, endpoint, json=payload, headers=request_headers)
                response.raise_for_status() # Raise exception for 4xx/5xx errors
                return response.json()

        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(f"Request failed: {error_message}")
            # Try to parse error details from response if available
            try:
                error_details = e.response.json()
                message = error_details.get('detail', error_message)
            except json.JSONDecodeError:
                message = error_message
            raise DeepSearchError(status_code=e.response.status_code, message=message) from e

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.timeout}s: {e}")
            raise DeepSearchError(message=f"Request timed out: {e}") from e

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise DeepSearchError(message=f"Request error: {e}") from e

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise DeepSearchError(message=f"Invalid JSON response from API: {e}") from e

        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            raise DeepSearchError(message=f"An unexpected error occurred: {e}") from e

    async def _stream_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handles streaming requests using Server-Sent Events (SSE)."""
        try:
            async with self.client.stream(method, endpoint, json=payload, headers=headers) as response:
                # Check for initial errors before starting to stream
                if response.status_code >= 400:
                    error_body = await response.aread()
                    error_message = f"HTTP error {response.status_code}: {error_body.decode()}"
                    logger.error(f"Streaming request failed: {error_message}")
                    # Try to parse error details
                    try:
                        error_details = json.loads(error_body)
                        message = error_details.get('detail', error_message)
                    except json.JSONDecodeError:
                        message = error_message
                    raise DeepSearchError(status_code=response.status_code, message=message)

                # Process SSE stream
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            logger.info("Stream finished with [DONE] marker.")
                            break
                        if data_str:
                            try:
                                chunk_data = json.loads(data_str)
                                # Validate chunk structure (optional but recommended)
                                try:
                                    DeepSearchChatChunk.model_validate(chunk_data)
                                except ValidationError as ve:
                                    logger.warning(f"Received stream chunk failed validation: {ve}. Chunk: {chunk_data}")
                                yield chunk_data
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode stream data line: {data_str}")
                    elif line.strip(): # Log other non-empty lines if needed
                         logger.debug(f"Received non-data line in stream: {line}")

        except httpx.HTTPStatusError as e:
            # This might catch errors if status check happens after stream starts (less common)
            error_message = f"HTTP error {e.response.status_code} during stream: {e.response.text}"
            logger.error(f"Streaming request failed: {error_message}")
            raise DeepSearchError(status_code=e.response.status_code, message=error_message) from e
        except httpx.TimeoutException as e:
            logger.error(f"Stream timed out after {self.timeout}s: {e}")
            raise DeepSearchError(message=f"Stream timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"Stream request error: {e}")
            raise DeepSearchError(message=f"Stream request error: {e}") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred during streaming: {e}")
            raise DeepSearchError(message=f"An unexpected error occurred during streaming: {e}") from e

    async def chat_completion(
        self, params: DeepSearchChatInput
    ) -> Union[DeepSearchChatOutput, AsyncGenerator[DeepSearchChatChunk, None]]:
        """
        Executes a chat completion request using the DeepSearch engine.

        Args:
            params: The input parameters for the chat completion.

        Returns:
            If stream=False, returns a DeepSearchChatOutput object.
            If stream=true, returns an async generator yielding DeepSearchChatChunk objects.

        Raises:
            DeepSearchError: If the API request fails.
            ValidationError: If the response data doesn't match the expected Pydantic model.
        """
        payload = params.model_dump(exclude_none=True) # Exclude optional fields not set
        logger.info(f"Sending chat completion request to {self.base_url}{self.endpoint} (stream={params.stream})")
        # logger.debug(f"Request payload: {payload}") # Be careful logging sensitive data

        response_data = await self._request(
            method="POST",
            endpoint=self.endpoint,
            payload=payload,
            stream=params.stream
        )

        if params.stream:
            # The response_data is already the async generator from _stream_request
            async def validated_generator() -> AsyncGenerator[DeepSearchChatChunk, None]:
                try:
                    async for chunk in response_data:
                        try:
                            yield DeepSearchChatChunk.model_validate(chunk)
                        except ValidationError as e:
                            logger.error(f"Stream chunk validation failed: {e}. Chunk: {chunk}")
                            # Decide whether to yield anyway, raise, or skip
                            # For now, we log and skip the invalid chunk
                            continue
                except DeepSearchError as e:
                    logger.error(f"Error consuming stream generator: {e}")
                    # Re-raise or handle as needed; FastMCP might handle exceptions from generators
                    raise
            return validated_generator()
        else:
            # Validate and return the single response object
            try:
                validated_output = DeepSearchChatOutput.model_validate(response_data)
                logger.info("Received successful non-streaming chat completion response.")
                return validated_output
            except ValidationError as e:
                logger.error(f"Non-streaming response validation failed: {e}. Response: {response_data}")
                raise DeepSearchError(message=f"Invalid response structure: {e}") from e
