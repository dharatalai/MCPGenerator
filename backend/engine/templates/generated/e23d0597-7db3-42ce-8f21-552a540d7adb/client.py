import os
import json
import logging
from typing import Optional, AsyncGenerator, Dict, Any

import httpx
from pydantic import ValidationError

from models import DeepSearchChatParams, DeepSearchChatResponse, DeepSearchChatChunk

logger = logging.getLogger(__name__)

# Define a custom exception for API errors
class DeepSearchApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"DeepSearch API Error {status_code}: {detail}")

class DeepSearchClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai/v1"
    DEFAULT_TIMEOUT = 120.0 # Increased timeout, especially for non-streaming

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        """Initializes the DeepSearchClient.

        Args:
            api_key: Your Jina AI API key (optional, increases rate limits).
            base_url: The base URL for the DeepSearch API.
            timeout: Default request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info("Jina API Key found, using Authorization header.")
        else:
            logger.warning("Jina API Key not provided. Using default rate limits.")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[httpx.Response, AsyncGenerator[str, None]]:
        """Makes an HTTP request to the DeepSearch API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url}")
        try:
            if stream:
                # For streaming, we return the response object to be iterated over
                req = self.client.build_request(method, endpoint, params=params, json=json_data)
                return await self.client.send(req, stream=True)
            else:
                response = await self.client.request(method, endpoint, params=params, json=json_data)
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
                return response
        except httpx.HTTPStatusError as e:
            # Attempt to parse error details from response body
            error_detail = f"HTTP Error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and 'detail' in error_data:
                    error_detail = error_data['detail']
                    if isinstance(error_detail, list) and error_detail:
                         error_detail = error_detail[0].get('msg', str(error_detail[0]))
                    elif isinstance(error_detail, dict):
                         error_detail = error_detail.get('message', str(error_detail))
                else:
                    error_detail = e.response.text or error_detail
            except (json.JSONDecodeError, ValueError):
                error_detail = e.response.text or error_detail

            logger.error(f"HTTP Error contacting DeepSearch API: {e.response.status_code} - {error_detail}")
            raise DeepSearchApiError(status_code=e.response.status_code, detail=error_detail) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request to DeepSearch API timed out: {e}")
            raise # Re-raise TimeoutException to be handled by the caller
        except httpx.RequestError as e:
            logger.error(f"Network error contacting DeepSearch API: {e}")
            raise # Re-raise RequestError
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}", exc_info=True)
            raise DeepSearchApiError(status_code=500, detail=f"Unexpected client error: {str(e)}") from e

    async def chat_completion_no_stream(self, params: DeepSearchChatParams) -> DeepSearchChatResponse:
        """Performs a non-streaming chat completion request."""
        if params.stream:
            logger.warning("stream=True passed to non-streaming method, overriding to False.")
            params.stream = False

        payload = params.model_dump(exclude_none=True)
        logger.info(f"Sending non-streaming request to /chat/completions with model {params.model}")
        logger.debug(f"Payload: {payload}")

        response = await self._request("POST", "/chat/completions", json_data=payload, stream=False)

        try:
            response_data = response.json()
            logger.debug(f"Received non-streaming response: {response_data}")
            return DeepSearchChatResponse(**response_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {response.text}", exc_info=True)
            raise DeepSearchApiError(status_code=500, detail=f"Invalid JSON response from server: {e}") from e
        except ValidationError as e:
            logger.error(f"Failed to validate response data: {response_data}", exc_info=True)
            raise DeepSearchApiError(status_code=500, detail=f"Invalid response structure from server: {e}") from e

    async def chat_completion_stream(self, params: DeepSearchChatParams) -> AsyncGenerator[DeepSearchChatChunk, None]:
        """Performs a streaming chat completion request.

        Yields:
            DeepSearchChatChunk: Chunks of the response as they arrive.
        """
        if not params.stream:
            logger.warning("stream=False passed to streaming method, overriding to True.")
            params.stream = True

        payload = params.model_dump(exclude_none=True)
        logger.info(f"Sending streaming request to /chat/completions with model {params.model}")
        logger.debug(f"Payload: {payload}")

        response_stream = await self._request("POST", "/chat/completions", json_data=payload, stream=True)

        try:
            async for line in response_stream.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        logger.info("Stream finished with [DONE] message.")
                        break
                    if not data_str:
                        logger.debug("Received empty data line, skipping.")
                        continue

                    try:
                        chunk_data = json.loads(data_str)
                        logger.debug(f"Received stream chunk: {chunk_data}")
                        yield DeepSearchChatChunk(**chunk_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode stream chunk JSON: '{data_str}'. Error: {e}")
                        continue # Skip malformed chunk
                    except ValidationError as e:
                        logger.warning(f"Failed to validate stream chunk: {chunk_data}. Error: {e}")
                        continue # Skip invalid chunk structure
                elif line:
                    logger.warning(f"Received unexpected line in stream: '{line}'")

        except DeepSearchApiError: # Re-raise API errors caught during initial request
             raise
        except httpx.HTTPError as e:
            # Errors during streaming might manifest here
            logger.error(f"HTTP error during streaming: {e}", exc_info=True)
            raise DeepSearchApiError(status_code=getattr(e, 'response', None) and e.response.status_code or 500, detail=f"HTTP error during stream: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during streaming: {e}", exc_info=True)
            raise DeepSearchApiError(status_code=500, detail=f"Unexpected client error during stream: {str(e)}") from e
        finally:
            if 'response_stream' in locals() and response_stream is not None:
                await response_stream.aclose()
            logger.debug("Stream closed.")

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("DeepSearchClient closed.")
