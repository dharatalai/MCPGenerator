import httpx
import os
import logging
from typing import Dict, Any, AsyncGenerator
from .models import DeepSearchChatInput, DeepSearchChatOutput
import json

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---

class DeepSearchError(Exception):
    """Base exception for DeepSearch client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)

class AuthenticationError(DeepSearchError):
    """Raised for 401/403 errors."""
    pass

class RateLimitError(DeepSearchError):
    """Raised for 429 errors."""
    pass

class BadRequestError(DeepSearchError):
    """Raised for 400 errors."""
    pass

class APIError(DeepSearchError):
    """Raised for 5xx server errors."""
    pass

class TimeoutError(DeepSearchError):
    """Raised for request timeouts."""
    pass

class ConnectionError(DeepSearchError):
    """Raised for network connection errors."""
    pass

# --- API Client ---

class DeepSearchClient:
    """Asynchronous client for interacting with the Jina DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 120.0):
        """
        Initializes the DeepSearchClient.

        Args:
            api_key: Jina API key. Defaults to JINA_API_KEY environment variable.
            base_url: Base URL for the DeepSearch API. Defaults to DEEPSEARCH_BASE_URL environment variable or 'https://deepsearch.jina.ai'.
            timeout: Request timeout in seconds. Defaults to 120.0 (especially important for non-streaming).
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key is required. Set JINA_API_KEY environment variable or pass it during initialization.")

        self.base_url = base_url or os.getenv("DEEPSEARCH_BASE_URL", "https://deepsearch.jina.ai")
        self.endpoint = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Ensure we accept JSON responses
        }
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout
        )

    async def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method to make non-streaming POST requests."""
        try:
            response = await self.client.post(self.endpoint, json=payload)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"DeepSearch request timed out: {e}")
            raise TimeoutError(f"Request timed out after {self.client.timeout.read} seconds.") from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_detail = e.response.text
            logger.error(f"DeepSearch HTTP error: {status_code} - {error_detail}")
            if status_code in (401, 403):
                raise AuthenticationError(f"Authentication failed (Status {status_code}): {error_detail}", status_code) from e
            elif status_code == 429:
                raise RateLimitError(f"Rate limit exceeded (Status {status_code}): {error_detail}", status_code) from e
            elif status_code == 400:
                raise BadRequestError(f"Bad request (Status {status_code}): {error_detail}", status_code) from e
            elif 500 <= status_code < 600:
                raise APIError(f"DeepSearch server error (Status {status_code}): {error_detail}", status_code) from e
            else:
                raise DeepSearchError(f"HTTP error (Status {status_code}): {error_detail}", status_code) from e
        except httpx.RequestError as e:
            logger.error(f"DeepSearch connection error: {e}")
            raise ConnectionError(f"Network error connecting to DeepSearch API: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during DeepSearch request: {e}")
            raise DeepSearchError(f"An unexpected error occurred: {str(e)}") from e

    async def _stream_request(self, payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Internal method to make streaming POST requests."""
        try:
            async with self.client.stream("POST", self.endpoint, json=payload) as response:
                # Check initial status before starting iteration
                if response.status_code >= 400:
                    error_detail = await response.aread()
                    status_code = response.status_code
                    logger.error(f"DeepSearch HTTP error on stream start: {status_code} - {error_detail.decode()}")
                    if status_code in (401, 403):
                        raise AuthenticationError(f"Authentication failed (Status {status_code}): {error_detail.decode()}", status_code)
                    elif status_code == 429:
                        raise RateLimitError(f"Rate limit exceeded (Status {status_code}): {error_detail.decode()}", status_code)
                    elif status_code == 400:
                        raise BadRequestError(f"Bad request (Status {status_code}): {error_detail.decode()}", status_code)
                    elif 500 <= status_code < 600:
                        raise APIError(f"DeepSearch server error (Status {status_code}): {error_detail.decode()}", status_code)
                    else:
                        raise DeepSearchError(f"HTTP error (Status {status_code}): {error_detail.decode()}", status_code)

                # Process Server-Sent Events (SSE)
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            logger.info("DeepSearch stream finished.")
                            break
                        try:
                            chunk = json.loads(data_str)
                            yield chunk
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode JSON chunk: {data_str}")
                    elif line:
                        logger.debug(f"Received non-data line: {line}")

        except httpx.TimeoutException as e:
            logger.error(f"DeepSearch stream request timed out: {e}")
            raise TimeoutError(f"Stream request timed out after {self.client.timeout.read} seconds.") from e
        except httpx.RequestError as e:
            logger.error(f"DeepSearch stream connection error: {e}")
            raise ConnectionError(f"Network error connecting to DeepSearch API during stream: {e}") from e
        except Exception as e:
            # Catch potential errors during stream processing or initial connection
            # Check if it's an HTTPStatusError potentially wrapped
            if isinstance(e, httpx.HTTPStatusError):
                 status_code = e.response.status_code
                 error_detail = e.response.text
                 logger.error(f"DeepSearch HTTP error during stream: {status_code} - {error_detail}")
                 if status_code in (401, 403): raise AuthenticationError(f"Authentication failed (Status {status_code}): {error_detail}", status_code) from e # type: ignore
                 if status_code == 429: raise RateLimitError(f"Rate limit exceeded (Status {status_code}): {error_detail}", status_code) from e # type: ignore
                 if status_code == 400: raise BadRequestError(f"Bad request (Status {status_code}): {error_detail}", status_code) from e # type: ignore
                 if 500 <= status_code < 600: raise APIError(f"DeepSearch server error (Status {status_code}): {error_detail}", status_code) from e # type: ignore
                 raise DeepSearchError(f"HTTP error (Status {status_code}): {error_detail}", status_code) from e # type: ignore
            else:
                logger.error(f"An unexpected error occurred during DeepSearch stream request: {e}")
                raise DeepSearchError(f"An unexpected error occurred during stream: {str(e)}") from e

    async def chat_completion(self, params: DeepSearchChatInput) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        """
        Performs iterative search, reading, and reasoning using the DeepSearch model.

        Args:
            params: Input parameters including messages, model, and other options.

        Returns:
            If stream=False, returns a dictionary representing the DeepSearchChatOutput.
            If stream=True, returns an async generator yielding dictionaries for each chunk.

        Raises:
            AuthenticationError: Invalid or missing API key.
            RateLimitError: Exceeded API request limits.
            TimeoutError: Request timed out.
            BadRequestError: Invalid input parameters or message format.
            APIError: Server-side errors on the DeepSearch API.
            ConnectionError: Network issues connecting to the API.
            DeepSearchError: Other unexpected errors.
        """
        payload = params.model_dump(exclude_none=True) # Use model_dump for Pydantic v2
        logger.info(f"Sending request to DeepSearch: model={params.model}, stream={params.stream}")
        # logger.debug(f"Payload: {payload}") # Be careful logging potentially large message content

        if params.stream:
            logger.info("Initiating streaming request.")
            return self._stream_request(payload)
        else:
            logger.info("Initiating non-streaming request.")
            result = await self._request(payload)
            # Validate or parse the result into DeepSearchChatOutput if needed, but
            # for simplicity, we return the raw dict for now.
            # You could add: return DeepSearchChatOutput(**result).model_dump()
            return result

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("DeepSearchClient closed.")
