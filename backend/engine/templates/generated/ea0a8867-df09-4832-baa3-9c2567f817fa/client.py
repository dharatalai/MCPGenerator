import httpx
import os
import logging
import json
from typing import Dict, Any, AsyncGenerator, Optional
from pydantic import ValidationError

from models import DeepSearchChatParams, ChatCompletionResponse, ChatCompletionChunk, Message

logger = logging.getLogger(__name__)

class DeepSearchError(Exception):
    """Custom exception for DeepSearch API errors."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"DeepSearch API Error {status_code}: {message}")

class DeepSearchClient:
    """Client for interacting with the Jina AI DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai/v1"
    DEFAULT_TIMEOUT = 120.0 # Increased timeout for potentially long searches

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("JINA_API_KEY environment variable not set.")

        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Explicitly accept JSON for non-streaming
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
        payload: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> httpx.Response:
        """Makes an HTTP request to the DeepSearch API."""
        logger.info(f"Making {method} request to {endpoint} (stream={stream})")
        if payload:
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

        try:
            if stream:
                # For streaming, we need different headers and use stream context
                stream_headers = self.headers.copy()
                stream_headers["Accept"] = "text/event-stream"
                req = self.client.build_request(method, endpoint, json=payload, headers=stream_headers)
                response = await self.client.send(req, stream=True)
            else:
                response = await self.client.request(method, endpoint, json=payload)

            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
            logger.info(f"Request successful (Status: {response.status_code})")
            return response

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.timeout}s: {e}")
            raise DeepSearchError(status_code=408, message=f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.text}"
            try:
                # Attempt to parse error details from response body
                error_details = e.response.json()
                error_message = error_details.get('detail', error_message)
            except json.JSONDecodeError:
                pass # Use the raw text if JSON parsing fails

            logger.error(error_message)
            status_code = e.response.status_code
            if status_code == 401:
                raise DeepSearchError(status_code=status_code, message="Authentication failed. Check your JINA_API_KEY.")
            elif status_code == 429:
                raise DeepSearchError(status_code=status_code, message=f"Rate limit exceeded. Details: {error_message}")
            elif status_code == 400:
                 raise DeepSearchError(status_code=status_code, message=f"Invalid request (400): {error_message}")
            else:
                raise DeepSearchError(status_code=status_code, message=error_message)
        except httpx.RequestError as e:
            logger.error(f"An unexpected network error occurred: {e}")
            raise DeepSearchError(status_code=500, message=f"Network error: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during request: {e}", exc_info=True)
            raise DeepSearchError(status_code=500, message=f"Unexpected error: {e}")

    async def chat_completion(
        self,
        params: DeepSearchChatParams
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Performs a deep search chat completion.

        Args:
            params: The parameters for the chat completion.

        Returns:
            If stream=False, returns a dictionary representing the ChatCompletionResponse.
            If stream=True, returns an async generator yielding dictionaries representing ChatCompletionChunks.
        """
        endpoint = "/chat/completions"
        # Use Pydantic's dict method to handle serialization and exclude None values
        payload = params.dict(exclude_none=True)

        if params.stream:
            # Return the async generator directly for streaming
            return self._process_stream(endpoint, payload)
        else:
            # Make a non-streaming request and parse the response
            response = await self._request("POST", endpoint, payload=payload, stream=False)
            try:
                response_data = response.json()
                # Validate response structure (optional but recommended)
                # ChatCompletionResponse.parse_obj(response_data)
                logger.debug(f"Received non-streaming response: {json.dumps(response_data, indent=2)}")
                return response_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {e}. Response text: {response.text}")
                raise DeepSearchError(status_code=500, message="Invalid JSON response from server")
            except ValidationError as e:
                logger.error(f"Response validation failed: {e}")
                raise DeepSearchError(status_code=500, message=f"Invalid response structure: {e}")

    async def _process_stream(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Processes the SSE stream from the API."""
        try:
            response = await self._request("POST", endpoint, payload=payload, stream=True)
            buffer = ""
            async for line in response.aiter_lines():
                if not line:
                    # End of an event
                    if buffer.startswith("data: "):
                        data_str = buffer[len("data: "):].strip()
                        if data_str == "[DONE]":
                            logger.info("Stream finished with [DONE] message.")
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            # Validate chunk structure (optional)
                            # ChatCompletionChunk.parse_obj(chunk_data)
                            logger.debug(f"Received stream chunk: {json.dumps(chunk_data)}")
                            yield chunk_data
                        except json.JSONDecodeError:
                            logger.warning(f"Could not decode JSON from stream data: {data_str}")
                        except ValidationError as e:
                            logger.warning(f"Stream chunk validation failed: {e}. Chunk: {data_str}")
                        except Exception as e:
                             logger.error(f"Error processing stream chunk: {e}. Chunk: {data_str}", exc_info=True)
                    buffer = ""
                else:
                    buffer += line + "\
"

        except DeepSearchError as e:
            # Logged in _request, re-raise or handle if needed
            logger.error(f"DeepSearchError during streaming: {e}")
            raise # Re-raise the specific error
        except Exception as e:
            logger.error(f"An unexpected error occurred during streaming: {e}", exc_info=True)
            raise DeepSearchError(status_code=500, message=f"Unexpected streaming error: {e}")
        finally:
            if 'response' in locals() and response is not None:
                await response.aclose()
            logger.info("Stream processing finished.")

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("DeepSearchClient closed.")
