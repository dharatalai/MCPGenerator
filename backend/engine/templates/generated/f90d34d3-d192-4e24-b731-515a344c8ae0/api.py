import httpx
import os
import logging
from typing import AsyncGenerator, Dict, Any
import json

from models import DeepSearchChatParams

logger = logging.getLogger(__name__)

# Default timeout for non-streaming requests (seconds)
# Increased significantly due to potential long processing times, even though streaming is preferred.
DEFAULT_TIMEOUT = 300.0
# Timeout for establishing a connection
CONNECT_TIMEOUT = 10.0

class JinaDeepSearchAPIClient:
    """Asynchronous client for interacting with the Jina DeepSearch API."""

    def __init__(self):
        """Initializes the API client, loading configuration from environment variables."""
        self.api_key = os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("JINA_API_KEY environment variable not set.")

        self.base_url = "https://deepsearch.jina.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json", # Ensure JSON responses
        }
        self._client = None

    async def get_client(self) -> httpx.AsyncClient:
        """Returns an initialized httpx.AsyncClient instance."""
        if self._client is None or self._client.is_closed:
            logger.info("Initializing httpx.AsyncClient for Jina DeepSearch")
            # Separate timeouts for connect vs read/write
            timeout_config = httpx.Timeout(DEFAULT_TIMEOUT, connect=CONNECT_TIMEOUT)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=timeout_config,
                event_hooks={'response': [self._log_response], 'request': [self._log_request]}
            )
        return self._client

    async def _log_request(self, request: httpx.Request):
        """Logs outgoing request details (excluding sensitive headers)."""
        # Avoid logging Authorization header
        headers = {k: v for k, v in request.headers.items() if k.lower() != 'authorization'}
        try:
            content = json.loads(request.content) if request.content else "<No Body>"
        except json.JSONDecodeError:
            content = "<Non-JSON Body>"
        logger.debug(f"--> {request.method} {request.url}\
Headers: {headers}\
Body: {content}")

    async def _log_response(self, response: httpx.Response):
        """Logs incoming response details."""
        # Ensure response content is read before logging if it's a streaming response
        # This might interfere with streaming if not handled carefully, logging only status for streams.
        if 'stream' in str(response.request.url):
             logger.debug(f"<-- {response.request.method} {response.request.url} - Status {response.status_code} (Streaming)")
        else:
            await response.aread()
            try:
                content = response.json()
            except json.JSONDecodeError:
                content = response.text
            logger.debug(f"<-- {response.request.method} {response.request.url} - Status {response.status_code}\
Body: {content}")


    async def chat_completion_stream(self, params: DeepSearchChatParams) -> AsyncGenerator[bytes, None]:
        """
        Performs a chat completion request to Jina DeepSearch and streams the response.

        Args:
            params: The parameters for the chat completion request.

        Yields:
            Bytes representing Server-Sent Events (SSE).

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            httpx.TimeoutException: If the request times out.
            Exception: For other unexpected errors.
        """
        client = await self.get_client()
        endpoint = "/v1/chat/completions"
        # Ensure stream is True for this method
        payload = params.model_dump(exclude_none=True)
        payload['stream'] = True

        logger.info(f"Initiating stream request to {self.base_url}{endpoint}")
        try:
            async with client.stream("POST", endpoint, json=payload) as response:
                # Raise exceptions for 4xx/5xx responses immediately
                if response.status_code >= 400:
                    # Attempt to read body for error details, even on stream
                    error_body = await response.aread()
                    try:
                        error_details = json.loads(error_body.decode())
                    except json.JSONDecodeError:
                        error_details = error_body.decode()
                    logger.error(f"API Error {response.status_code}: {error_details}")
                    response.raise_for_status() # Raise HTTPStatusError

                # Stream the response content chunks
                async for chunk in response.aiter_bytes():
                    yield chunk

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise  # Re-raise the original exception
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during chat completion stream: {e}")
            raise

    async def close(self):
        """Closes the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("Closed httpx.AsyncClient for Jina DeepSearch")
        self._client = None
