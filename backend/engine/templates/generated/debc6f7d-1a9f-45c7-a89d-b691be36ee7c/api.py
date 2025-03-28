import httpx
import os
import logging
import json
from typing import AsyncIterator, Union, Optional
from pydantic import ValidationError

from models import DeepSearchChatInput, DeepSearchChunk, DeepSearchResponse

logger = logging.getLogger(__name__) 

# Custom Exception for API specific errors
class JinaAPIError(Exception):
    def __init__(self, status_code: int, error_info: dict):
        self.status_code = status_code
        self.error_info = error_info
        super().__init__(f"Jina API Error {status_code}: {error_info}")

class JinaAuthenticationError(JinaAPIError):
    def __init__(self, error_info: dict):
        super().__init__(401, error_info)

class JinaDeepSearchClient:
    """Asynchronous client for interacting with the Jina DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai/v1"
    DEFAULT_TIMEOUT = 180.0  # seconds, increased for potentially long searches

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("JINA_API_KEY environment variable not set.")

        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Ensure JSON responses are requested
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def _parse_sse_event(self, line: str) -> Optional[DeepSearchChunk]:
        """Parses a single Server-Sent Event line."""
        line = line.strip()
        if not line or line.startswith(":"):
            return None
        if line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                logger.info("Received [DONE] marker from Jina API stream.")
                return None
            try:
                data_json = json.loads(data_str)
                return DeepSearchChunk.model_validate(data_json)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from SSE data: {data_str!r}")
                return None # Or raise an error?
            except ValidationError as e:
                logger.error(f"Failed to validate DeepSearchChunk from SSE data: {data_str!r}\
Error: {e}")
                return None # Or raise an error?
        else:
            logger.warning(f"Received unexpected SSE line format: {line!r}")
            return None

    async def _stream_chat_completion(self, payload: dict) -> AsyncIterator[DeepSearchChunk]:
        """Handles the streaming chat completion request."""
        endpoint = "/chat/completions"
        try:
            async with self.client.stream("POST", endpoint, json=payload) as response:
                # Check for initial errors before starting to stream
                if response.status_code >= 400:
                    try:
                        error_body = await response.aread()
                        error_info = json.loads(error_body.decode())
                    except Exception:
                        error_info = {"error": f"HTTP {response.status_code}", "detail": response.reason_phrase}
                    
                    if response.status_code == 401:
                        raise JinaAuthenticationError(error_info)
                    else:
                        raise JinaAPIError(response.status_code, error_info)
                
                # Process the stream
                async for line in response.aiter_lines():
                    chunk = await self._parse_sse_event(line)
                    if chunk:
                        yield chunk

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.client.timeout}s: {e}")
            raise TimeoutError(f"Jina API request timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
            raise ConnectionError(f"Could not connect to Jina API: {e}") from e
        except JinaAPIError: # Re-raise specific API errors
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during streaming chat completion: {e}")
            raise RuntimeError(f"Unexpected error during streaming: {e}") from e

    async def _non_stream_chat_completion(self, payload: dict) -> DeepSearchResponse:
        """Handles the non-streaming chat completion request."""
        endpoint = "/chat/completions"
        try:
            response = await self.client.post(endpoint, json=payload)
            
            # Check for HTTP errors
            if response.status_code >= 400:
                try:
                    error_info = response.json()
                except json.JSONDecodeError:
                     error_info = {"error": f"HTTP {response.status_code}", "detail": response.reason_phrase}
                
                if response.status_code == 401:
                    raise JinaAuthenticationError(error_info)
                else:
                    # Note: Non-streaming requests might hit gateway timeouts (e.g., 504) for long tasks
                    if response.status_code == 504:
                         logger.warning("Received 504 Gateway Timeout. Consider using stream=True for long tasks.")
                    raise JinaAPIError(response.status_code, error_info)
            
            # Parse successful response
            response_data = response.json()
            return DeepSearchResponse.model_validate(response_data)

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.client.timeout}s: {e}")
            raise TimeoutError(f"Jina API request timed out: {e}. Consider using stream=True.") from e
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
            raise ConnectionError(f"Could not connect to Jina API: {e}") from e
        except ValidationError as e:
            logger.error(f"Failed to validate DeepSearchResponse: {e}\
Response data: {response_data!r}")
            raise ValueError(f"Invalid response structure received from Jina API: {e}") from e
        except JinaAPIError: # Re-raise specific API errors
             raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during non-streaming chat completion: {e}")
            raise RuntimeError(f"Unexpected error: {e}") from e

    async def chat_completion(self, params: DeepSearchChatInput) -> Union[AsyncIterator[DeepSearchChunk], DeepSearchResponse]:
        """
        Performs deep search and reasoning based on conversation history.

        Args:
            params: The input parameters conforming to DeepSearchChatInput model.

        Returns:
            If stream=True, an async iterator yielding DeepSearchChunk objects.
            If stream=False, a single DeepSearchResponse object.

        Raises:
            JinaAuthenticationError: If the API key is invalid.
            JinaAPIError: For other API-related errors (4xx, 5xx).
            TimeoutError: If the request times out.
            ConnectionError: If there's a network issue connecting to the API.
            ValueError: If the API response structure is invalid.
            RuntimeError: For unexpected errors.
        """
        # Use model_dump to serialize Pydantic model, excluding None values
        # Use by_alias=False to ensure correct field names are sent
        payload = params.model_dump(exclude_none=True, by_alias=False)
        logger.info(f"Sending request to Jina DeepSearch: stream={params.stream}")
        # logger.debug(f"Payload: {payload}") # Be careful logging potentially sensitive message content

        if params.stream:
            return self._stream_chat_completion(payload)
        else:
            # Warn about potential timeouts with non-streaming
            logger.warning("Executing non-streaming request. This might time out for complex queries. Consider using stream=True.")
            return await self._non_stream_chat_completion(payload)
