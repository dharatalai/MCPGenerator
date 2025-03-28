import httpx
import os
import logging
import json
from typing import AsyncGenerator, Dict, Any
from models import DeepSearchChatParams, DeepSearchResponse

logger = logging.getLogger(__name__)

class JinaDeepSearchClient:
    """Asynchronous client for interacting with the Jina DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai"
    API_ENDPOINT = "/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 180.0):
        """
        Initializes the Jina DeepSearch API client.

        Args:
            api_key: The Jina API key. Reads from JINA_API_KEY env var if not provided.
            base_url: The base URL for the Jina DeepSearch API. Reads from JINA_DEEPSEARCH_BASE_URL env var or uses default if not provided.
            timeout: Default timeout for API requests in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = base_url or os.getenv("JINA_DEEPSEARCH_BASE_URL") or self.DEFAULT_BASE_URL

        if not self.api_key:
            logger.warning("JINA_API_KEY not found. API calls may be rate-limited (2 RPM).")
            self.headers = {"Content-Type": "application/json"}
        else:
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def chat_completion(self, params: DeepSearchChatParams) -> AsyncGenerator[DeepSearchResponse, None] | DeepSearchResponse:
        """
        Performs a chat completion request to the Jina DeepSearch API.

        Handles both streaming and non-streaming responses.

        Args:
            params: The parameters for the chat completion request.

        Returns:
            If stream=True, an async generator yielding DeepSearchResponse chunks.
            If stream=False, a single DeepSearchResponse object.

        Raises:
            httpx.HTTPStatusError: For API errors (4xx, 5xx).
            httpx.RequestError: For network-related errors.
            Exception: For unexpected errors during processing.
        """
        # Exclude None values from the payload, Pydantic v2 handles alias generation
        payload = params.model_dump(exclude_none=True, by_alias=False)
        # Ensure stream is explicitly in payload if True, as it's often expected by APIs
        payload['stream'] = params.stream

        request_url = self.API_ENDPOINT
        logger.info(f"Sending request to {self.base_url}{request_url} with stream={params.stream}")
        # logger.debug(f"Payload: {payload}") # Be cautious logging payload with potentially sensitive data

        try:
            if params.stream:
                return self._stream_request(request_url, payload)
            else:
                response = await self.client.post(request_url, json=payload)
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
                response_data = response.json()
                # logger.debug(f"Received non-streamed response: {response_data}")
                return DeepSearchResponse.model_validate(response_data)

        except httpx.HTTPStatusError as e:
            # Log specific API errors
            error_details = "No details available"
            try:
                error_details = e.response.json()
            except json.JSONDecodeError:
                error_details = e.response.text
            logger.error(f"API Error {e.response.status_code}: {error_details} for request to {e.request.url}")
            # Re-raise the original exception to be handled by the caller
            raise e
        except httpx.RequestError as e:
            # Log network errors (timeout, connection issues)
            logger.error(f"Network Error: {e.__class__.__name__} while requesting {e.request.url}: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during chat completion: {e.__class__.__name__}: {str(e)}")
            raise e

    async def _stream_request(self, url: str, payload: Dict[str, Any]) -> AsyncGenerator[DeepSearchResponse, None]:
        """Handles the streaming request and yields parsed chunks."""
        buffer = ""
        async with self.client.stream("POST", url, json=payload) as response:
            # Check for immediate errors before starting to stream
            if response.status_code >= 400:
                 error_content = await response.aread()
                 error_details = "Unknown error"
                 try:
                     error_details = json.loads(error_content.decode())
                 except json.JSONDecodeError:
                     error_details = error_content.decode()
                 logger.error(f"API Error {response.status_code} on stream initiation: {error_details}")
                 response.raise_for_status() # Raise HTTPStatusError

            async for line in response.aiter_lines():
                if not line.strip(): # Skip empty keep-alive lines
                    continue
                # logger.debug(f"Raw stream line: {line}")
                buffer += line + '\
'
                # Process buffer for complete SSE messages
                while '\
\
' in buffer:
                    message, buffer = buffer.split('\
\
', 1)
                    if message.startswith("data: "):
                        data_str = message[len("data: "):].strip()
                        if data_str == "[DONE]":
                            logger.info("Stream finished with [DONE] message.")
                            return # End of stream
                        try:
                            chunk_data = json.loads(data_str)
                            # logger.debug(f"Received stream chunk: {chunk_data}")
                            yield DeepSearchResponse.model_validate(chunk_data)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode JSON from stream chunk: {data_str}")
                        except Exception as e:
                            logger.error(f"Error processing stream chunk: {e.__class__.__name__}: {e}")
                    else:
                        logger.warning(f"Received unexpected stream message format: {message}")

        # Process any remaining buffer content after stream ends (should ideally be empty)
        if buffer.strip():
             logger.warning(f"Unexpected remaining buffer content after stream: {buffer}")
