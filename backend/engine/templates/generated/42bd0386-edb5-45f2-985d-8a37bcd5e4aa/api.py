import httpx
import logging
import os
import json
from typing import AsyncGenerator, Union, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models import DeepSearchChatInput, DeepSearchResponse, DeepSearchResponseChunk

logger = logging.getLogger(__name__)

# Define specific exceptions for clarity
class DeepSearchAPIError(Exception):
    """Custom exception for DeepSearch API errors."""
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"DeepSearch API Error {status_code}: {detail}")

class DeepSearchAPIClient:
    """Client for interacting with the Jina DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://deepsearch.jina.ai", timeout: float = 180.0):
        """
        Initializes the DeepSearch API client.

        Args:
            api_key: The Jina API key. Reads from JINA_API_KEY env var if not provided.
            base_url: The base URL for the DeepSearch API.
            timeout: Default timeout for API requests in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            logger.warning("JINA_API_KEY not found. Using DeepSearch without an API key, which has lower rate limits (2 RPM).")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        reraise=True # Reraise the exception after retries are exhausted
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[httpx.Response, AsyncGenerator[str, None]]:
        """Makes an HTTP request to the DeepSearch API with retry logic."""
        try:
            if stream:
                # For streaming, return the stream directly
                req = self.client.build_request(method, endpoint, json=payload)
                response_stream = await self.client.send(req, stream=True)
                response_stream.raise_for_status() # Raise HTTP errors immediately
                return response_stream
            else:
                response = await self.client.request(method, endpoint, json=payload)
                response.raise_for_status() # Raise HTTP errors (4xx, 5xx)
                return response

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                detail = e.response.json()
            except json.JSONDecodeError:
                detail = e.response.text
            logger.error(f"HTTP error {status_code} calling {e.request.url}: {detail}")
            raise DeepSearchAPIError(status_code=status_code, detail=detail) from e
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error calling {e.request.url}: {e}")
            raise # Reraised for retry logic
        except httpx.NetworkError as e:
            logger.error(f"Network error calling {e.request.url}: {e}")
            raise # Reraised for retry logic
        except Exception as e:
            logger.error(f"Unexpected error during API request to {endpoint}: {e}")
            raise DeepSearchAPIError(status_code=500, detail=str(e)) from e # Treat unexpected errors as internal

    async def chat_completion(
        self,
        params: DeepSearchChatInput
    ) -> Union[DeepSearchResponse, AsyncGenerator[DeepSearchResponseChunk, None]]:
        """
        Performs a deep search chat completion.

        Args:
            params: Input parameters conforming to DeepSearchChatInput model.

        Returns:
            If stream=False, returns a DeepSearchResponse object.
            If stream=True, returns an async generator yielding DeepSearchResponseChunk objects.

        Raises:
            DeepSearchAPIError: If the API returns an error.
        """
        endpoint = "/v1/chat/completions"
        # Use exclude_unset=True to only send parameters that were explicitly set
        payload = params.dict(exclude_unset=True)

        logger.info(f"Sending request to DeepSearch API: stream={params.stream}")
        # logger.debug(f"Payload: {payload}") # Be careful logging payload with potentially sensitive data

        if params.stream:
            response_stream = await self._make_request("POST", endpoint, payload=payload, stream=True)
            return self._process_stream(response_stream)
        else:
            response = await self._make_request("POST", endpoint, payload=payload, stream=False)
            try:
                response_data = response.json()
                logger.info("Received non-streaming response from DeepSearch API.")
                return DeepSearchResponse(**response_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {response.text}")
                raise DeepSearchAPIError(status_code=500, detail=f"Invalid JSON response: {e}") from e
            except Exception as e:
                logger.error(f"Error parsing non-streaming response: {e}")
                raise DeepSearchAPIError(status_code=500, detail=f"Error parsing response: {e}") from e

    async def _process_stream(
        self, response_stream: httpx.Response
    ) -> AsyncGenerator[DeepSearchResponseChunk, None]:
        """Processes the Server-Sent Events stream from the API."""
        buffer = ""
        async with response_stream:
            async for line_bytes in response_stream.aiter_lines():
                line = line_bytes.strip()
                # logger.debug(f"Received stream line: {line}")
                if not line:
                    # Empty line signifies end of an event
                    if buffer.startswith("data:"):
                        data_str = buffer[len("data:"):].strip()
                        if data_str == "[DONE]":
                            logger.info("Stream finished with [DONE] message.")
                            buffer = ""
                            break # End of stream
                        try:
                            data = json.loads(data_str)
                            chunk = DeepSearchResponseChunk(**data)
                            yield chunk
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode JSON chunk: {data_str}")
                        except Exception as e:
                            logger.error(f"Error processing stream chunk '{data_str}': {e}")
                    buffer = ""
                else:
                    buffer += line + "\
" # Rebuild potential multi-line data

            # Check if there's anything left in the buffer after loop finishes (e.g., if stream ends without empty line)
            if buffer.startswith("data:"):
                data_str = buffer[len("data:"):].strip()
                if data_str != "[DONE]":
                    try:
                        data = json.loads(data_str)
                        chunk = DeepSearchResponseChunk(**data)
                        yield chunk
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode final JSON chunk: {data_str}")
                    except Exception as e:
                        logger.error(f"Error processing final stream chunk '{data_str}': {e}")

        logger.info("Finished processing DeepSearch stream.")

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("DeepSearch API client closed.")
