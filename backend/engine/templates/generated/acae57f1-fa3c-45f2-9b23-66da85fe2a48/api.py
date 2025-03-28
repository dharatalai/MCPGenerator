import httpx
import os
import logging
import json
from typing import AsyncGenerator, Union, Dict, Any
from pydantic import ValidationError

from models import DeepSearchChatRequest, DeepSearchChatResponse, DeepSearchChatChunk

logger = logging.getLogger(__name__)

class DeepSearchApiClient:
    """Client for interacting with the Jina AI DeepSearch API."""

    def __init__(self):
        """Initializes the API client, loading configuration from environment variables."""
        self.api_key = os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("JINA_API_KEY environment variable not set.")

        self.base_url = os.getenv("JINA_DEEPSEARCH_BASE_URL", "https://deepsearch.jina.ai")
        self.api_endpoint = "/v1/chat/completions"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Important for non-streaming
        }
        # Increased timeout for potentially long reasoning/search, especially non-streaming
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=300.0)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def chat_completions(
        self,
        request_data: DeepSearchChatRequest
    ) -> Union[DeepSearchChatResponse, AsyncGenerator[DeepSearchChatChunk, None]]:
        """"""
        Calls the DeepSearch chat completions endpoint.

        Args:
            request_data: The request data conforming to DeepSearchChatRequest model.

        Returns:
            If stream=False, returns a DeepSearchChatResponse object.
            If stream=True, returns an async generator yielding DeepSearchChatChunk objects.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code (4xx or 5xx).
            httpx.RequestError: If there's a network issue connecting to the API.
            ValueError: If the response cannot be parsed.
            ValidationError: If the response data doesn't match the Pydantic models.
        """"
        payload = request_data.model_dump(exclude_none=True, by_alias=True)
        logger.info(f"Sending request to {self.base_url}{self.api_endpoint} with stream={request_data.stream}")
        # logger.debug(f"Request payload: {payload}") # Be cautious logging potentially sensitive message content

        try:
            if request_data.stream:
                return self._stream_chat_completions(payload)
            else:
                response = await self.client.post(self.api_endpoint, json=payload)
                response.raise_for_status() # Raise exception for 4xx/5xx errors
                response_json = response.json()
                logger.info("Received non-streaming response.")
                # logger.debug(f"Non-streaming response data: {response_json}")
                return DeepSearchChatResponse.model_validate(response_json)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            # Attempt to parse error details if available
            try:
                error_details = e.response.json()
            except json.JSONDecodeError:
                error_details = e.response.text
            raise httpx.HTTPStatusError(message=f"API Error: {error_details}", request=e.request, response=e.response)
        except httpx.RequestError as e:
            logger.error(f"Network error connecting to DeepSearch API: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Failed to validate API response: {e}")
            raise ValueError(f"Invalid response format received from API: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise ValueError(f"Failed to decode JSON response: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            raise

    async def _stream_chat_completions(
        self,
        payload: Dict[str, Any]
    ) -> AsyncGenerator[DeepSearchChatChunk, None]:
        """Handles the streaming response from the API."""
        try:
            async with self.client.stream("POST", self.api_endpoint, json=payload) as response:
                response.raise_for_status() # Check status before starting iteration
                logger.info("Streaming response started.")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[len("data: "):]
                        if data_str.strip() == "[DONE]":
                            logger.info("Streaming response finished ([DONE] received).")
                            break
                        if not data_str.strip():
                            continue
                        try:
                            chunk_json = json.loads(data_str)
                            # logger.debug(f"Received stream chunk: {chunk_json}")
                            yield DeepSearchChatChunk.model_validate(chunk_json)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid JSON data in stream: {data_str}")
                            continue
                        except ValidationError as e:
                            logger.warning(f"Skipping invalid chunk structure in stream: {e}. Data: {data_str}")
                            continue
                    elif line.strip(): # Log unexpected non-empty lines
                        logger.warning(f"Received unexpected line in stream: {line}")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during streaming: {e.response.status_code}")
            # Attempt to read body for more details, might fail if stream already started erroring
            try:
                error_body = await e.response.aread()
                logger.error(f"Error response body: {error_body.decode()}")
                error_details = error_body.decode()
            except Exception:
                error_details = "(Could not read error body)"
            # Raise a new error to stop the generator and signal the problem
            raise httpx.HTTPStatusError(message=f"API Error during stream: {error_details}", request=e.request, response=e.response)
        except httpx.RequestError as e:
            logger.error(f"Network error during streaming: {e}")
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during streaming: {e}")
            raise
