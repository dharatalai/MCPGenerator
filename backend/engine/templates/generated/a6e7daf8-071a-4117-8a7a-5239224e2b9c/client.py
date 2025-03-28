import httpx
import os
import logging
import json
import asyncio
from typing import AsyncGenerator, Union, Optional
from pydantic import ValidationError

from models import (
    DeepSearchChatInput,
    DeepSearchChatCompletion,
    DeepSearchChatCompletionChunk,
    DeepSearchUsage # Import Usage if needed for final chunk parsing
)

logger = logging.getLogger(__name__)

# Custom Exceptions
class DeepSearchError(Exception):
    """Base exception for DeepSearch client errors."""
    pass

class AuthenticationError(DeepSearchError):
    """Error for invalid or missing API key (401/403)."""
    pass

class RateLimitError(DeepSearchError):
    """Error for exceeding rate limits (429)."""
    pass

class BadRequestError(DeepSearchError):
    """Error for invalid input parameters (400)."""
    pass

class TimeoutError(DeepSearchError):
    """Error for request timeouts."""
    pass

class InternalServerError(DeepSearchError):
    """Error for server-side issues (5xx)."""
    pass

class NetworkError(DeepSearchError):
    """Error for network connectivity issues."""
    pass

class DeepSearchClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 180.0):
        """
        Initializes the DeepSearchClient.

        Args:
            api_key: Jina API Key. Defaults to JINA_API_KEY environment variable.
            base_url: Base URL for the DeepSearch API. Defaults to DEEPSEARCH_BASE_URL or https://deepsearch.jina.ai.
            timeout: Default request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API Key must be provided via argument or JINA_API_KEY environment variable.")

        self.base_url = base_url or os.getenv("DEEPSEARCH_BASE_URL", "https://deepsearch.jina.ai")
        self.endpoint = "/v1/chat/completions"
        self.timeout = timeout

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Ensure we accept JSON for non-streaming
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[dict] = None,
        stream: bool = False
    ) -> Union[httpx.Response, AsyncGenerator[str, None]]:
        """Makes an HTTP request to the DeepSearch API, handling potential errors."""
        try:
            if stream:
                # For streaming, we need to handle the response differently
                req = self.client.build_request(method, endpoint, json=payload)
                response_stream = await self.client.send(req, stream=True)
                # Raise status errors early for non-2xx responses before streaming
                response_stream.raise_for_status()
                return response_stream # Return the stream object
            else:
                response = await self.client.request(method, endpoint, json=payload)
                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
                return response

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise TimeoutError(f"Request timed out after {self.timeout} seconds.") from e
        except httpx.RequestError as e:
            logger.error(f"Network error occurred: {e}")
            # E.g., DNS resolution failure, connection refused
            raise NetworkError(f"Network error: {e}") from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            response_text = e.response.text
            logger.error(f"HTTP error {status_code}: {response_text}")
            if status_code in (401, 403):
                raise AuthenticationError(f"Authentication failed ({status_code}): {response_text}") from e
            elif status_code == 429:
                raise RateLimitError(f"Rate limit exceeded ({status_code}): {response_text}") from e
            elif status_code == 400:
                raise BadRequestError(f"Bad request ({status_code}): {response_text}") from e
            elif 500 <= status_code < 600:
                # Handle 524 specifically if needed, though httpx might raise TimeoutException earlier
                if status_code == 524:
                     raise TimeoutError(f"Server timeout ({status_code}): {response_text}") from e
                raise InternalServerError(f"Server error ({status_code}): {response_text}") from e
            else:
                raise DeepSearchError(f"Unhandled HTTP error ({status_code}): {response_text}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during the request: {e}")
            raise DeepSearchError(f"An unexpected error occurred: {e}") from e

    async def _process_sse_stream(
        self, response_stream: httpx.Response
    ) -> AsyncGenerator[DeepSearchChatCompletionChunk, None]:
        """Processes a Server-Sent Events (SSE) stream and yields parsed chunks."""
        buffer = ""
        async with response_stream:
            async for line in response_stream.aiter_lines():
                if not line.strip(): # Skip empty lines used as separators
                    continue
                if line.startswith(":"): # Skip comments
                    continue

                buffer += line
                # Check if the line indicates the end of a data block (often starts with 'data:')
                # and process complete messages (might span multiple lines)
                if line.startswith("data:"): # Process data lines
                    data_content = line[len("data:"):].strip()
                    if data_content == "[DONE]":
                        logger.info("Stream finished with [DONE] signal.")
                        break
                    try:
                        chunk_data = json.loads(data_content)
                        yield DeepSearchChatCompletionChunk.parse_obj(chunk_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON from SSE data: {data_content}")
                        # Continue, maybe part of a larger message, or log and skip
                    except ValidationError as e:
                        logger.warning(f"Failed to validate SSE chunk: {e}. Data: {data_content}")
                        # Decide whether to yield anyway or skip
                    except Exception as e:
                        logger.error(f"Error processing SSE chunk: {e}. Data: {data_content}")
                        # Decide how to handle unexpected errors during chunk processing

                # Reset buffer or handle multi-line data if necessary based on API specifics
                # Assuming here each 'data:' line is a complete JSON object for simplicity

    async def chat_completion(
        self, params: DeepSearchChatInput
    ) -> Union[AsyncGenerator[DeepSearchChatCompletionChunk, None], DeepSearchChatCompletion]:
        """
        Performs a deep search chat completion.

        Args:
            params: Input parameters for the chat completion.

        Returns:
            If stream=True, an async generator yielding DeepSearchChatCompletionChunk objects.
            If stream=False, a DeepSearchChatCompletion object.

        Raises:
            AuthenticationError, RateLimitError, BadRequestError,
            TimeoutError, InternalServerError, NetworkError, DeepSearchError
        """
        payload = params.dict(exclude_none=True) # Exclude optional fields not provided
        stream = params.stream

        logger.info(f"Sending chat completion request (stream={stream}) to {self.endpoint}")
        # Avoid logging sensitive message content in production if necessary
        # logger.debug(f"Request payload: {payload}")

        response_or_stream = await self._request("POST", self.endpoint, payload=payload, stream=stream)

        if stream:
            if not isinstance(response_or_stream, httpx.Response):
                 # Should not happen based on _request logic, but type checking helps
                 raise DeepSearchError("Expected httpx.Response for streaming, got something else.")
            logger.info("Processing SSE stream...")
            # Return the async generator directly
            return self._process_sse_stream(response_or_stream)
        else:
            if not isinstance(response_or_stream, httpx.Response):
                 raise DeepSearchError("Expected httpx.Response for non-streaming, got something else.")
            try:
                response_data = response_or_stream.json()
                logger.info("Received non-streaming response.")
                # logger.debug(f"Response data: {response_data}")
                return DeepSearchChatCompletion.parse_obj(response_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {e}. Response text: {response_or_stream.text}")
                raise DeepSearchError(f"Failed to decode JSON response: {e}") from e
            except ValidationError as e:
                logger.error(f"Failed to validate response data: {e}. Response data: {response_data}")
                raise DeepSearchError(f"Response validation failed: {e}") from e
