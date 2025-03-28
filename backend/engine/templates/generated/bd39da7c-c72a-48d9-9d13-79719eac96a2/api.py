import httpx
import os
import logging
import json
from typing import AsyncGenerator, Dict, Any, Union
from pydantic import ValidationError

from models import DeepSearchChatParams, DeepSearchChatResponse, DeepSearchChatStreamResponse

logger = logging.getLogger(__name__)

class DeepSearchClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai"
    API_ENDPOINT = "/v1/chat/completions"
    # DeepSearch can take a while, especially for complex queries or non-streaming.
    DEFAULT_TIMEOUT = 300.0 # 5 minutes

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        """
        Initializes the DeepSearchClient.

        Args:
            api_key: The Jina AI API key. Reads from JINA_API_KEY env var if not provided.
            base_url: The base URL for the DeepSearch API. Reads from DEEPSEARCH_BASE_URL or uses default if not provided.
            timeout: Default timeout for HTTP requests in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key not provided and JINA_API_KEY environment variable not set.")

        self.base_url = base_url or os.getenv("DEEPSEARCH_BASE_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Ensure we get JSON back for non-streaming
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def chat_completion(self, params: DeepSearchChatParams) -> Union[DeepSearchChatResponse, AsyncGenerator[DeepSearchChatStreamResponse, None]]:
        """
        Performs a chat completion request using the DeepSearch engine.

        Args:
            params: The parameters for the chat completion request.

        Returns:
            If stream=False, returns a DeepSearchChatResponse object.
            If stream=True, returns an async generator yielding DeepSearchChatStreamResponse objects.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code (4xx or 5xx).
            httpx.TimeoutException: If the request times out.
            httpx.RequestError: For other network-related errors.
            ValidationError: If the API response doesn't match the expected Pydantic model.
            ValueError: If parameters are invalid (though Pydantic should catch most).
            json.JSONDecodeError: If the response body is not valid JSON (for non-streaming).
        """
        payload = params.model_dump(exclude_none=True)
        request_kwargs = {
            "method": "POST",
            "url": self.API_ENDPOINT,
            "json": payload
        }

        try:
            if params.stream:
                logger.info(f"Initiating streaming chat completion request to {self.base_url}{self.API_ENDPOINT}")
                return self._stream_chat_completion(**request_kwargs)
            else:
                logger.info(f"Initiating non-streaming chat completion request to {self.base_url}{self.API_ENDPOINT}")
                response = await self.client.request(**request_kwargs)
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
                response_data = response.json()
                # Validate and return the full response
                validated_response = DeepSearchChatResponse.model_validate(response_data)
                logger.info(f"Received non-streaming response (ID: {validated_response.id})")
                return validated_response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            # You might want to raise a more specific exception or return an error structure
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Network request error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Response validation error: {e}")
            # Log the problematic data if possible and privacy allows
            # logger.error(f"Invalid data: {response_data}")
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during chat completion: {e}")
            raise

    async def _stream_chat_completion(self, **request_kwargs) -> AsyncGenerator[DeepSearchChatStreamResponse, None]:
        """Handles the streaming logic for chat completions using SSE."""
        buffer = ""
        try:
            async with self.client.stream(**request_kwargs) as response:
                response.raise_for_status() # Check status before starting iteration
                async for line in response.aiter_lines():
                    if not line:
                        # Empty lines separate events in SSE
                        if buffer.startswith("data:"): # Process completed buffer
                            data_str = buffer[len("data:"):].strip()
                            if data_str == "[DONE]":
                                logger.info("Stream finished with [DONE] marker.")
                                break # End of stream
                            try:
                                chunk_data = json.loads(data_str)
                                validated_chunk = DeepSearchChatStreamResponse.model_validate(chunk_data)
                                yield validated_chunk
                            except json.JSONDecodeError:
                                logger.warning(f"Skipping non-JSON data line in stream: {data_str}")
                            except ValidationError as e:
                                logger.warning(f"Stream chunk validation error: {e}. Data: {data_str}")
                            except Exception as e:
                                logger.exception(f"Error processing stream chunk: {e}. Data: {data_str}")
                        buffer = "" # Reset buffer after processing or if line wasn't data
                    else:
                        buffer += line + "\
" # Append line to buffer

                # Process any remaining buffer content after loop finishes (e.g., if stream ends without newline)
                if buffer.startswith("data:"):
                    data_str = buffer[len("data:"):].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            chunk_data = json.loads(data_str)
                            validated_chunk = DeepSearchChatStreamResponse.model_validate(chunk_data)
                            yield validated_chunk
                        except (json.JSONDecodeError, ValidationError) as e:\
                            logger.warning(f"Error processing final buffer content: {e}. Data: {data_str}")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during streaming: {e.response.status_code} - {await e.response.aread()}")
            # Reraise or handle appropriately. Cannot easily yield an error through generator.
            # Consider logging and stopping iteration.
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Stream request timed out: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Stream network request error: {e}")
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during streaming: {e}")
            raise
