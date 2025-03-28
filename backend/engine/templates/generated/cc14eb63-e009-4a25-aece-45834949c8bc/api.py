import httpx
import os
import logging
import json
from typing import AsyncIterator, Union, Optional
from pydantic import ValidationError

from models import DeepSearchChatInput, DeepSearchChatResponse, DeepSearchChatResponseChunk

logger = logging.getLogger(__name__)

class JinaDeepSearchClient:
    """Asynchronous client for the Jina AI DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai"
    API_ENDPOINT = "/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 180.0):
        """
        Initializes the JinaDeepSearchClient.

        Args:
            api_key: The Jina API key. Reads from JINA_API_KEY env var if not provided.
            base_url: The base URL for the Jina API. Defaults to https://deepsearch.jina.ai.
            timeout: Default timeout for API requests in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout

        if not self.api_key:
            logger.warning("JINA_API_KEY not found in environment variables. Rate limits will be lower (2 RPM).")
            self.headers = {"Content-Type": "application/json"}
        else:
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def chat_completion(self,
                              input_data: DeepSearchChatInput
                              ) -> Union[DeepSearchChatResponse, AsyncIterator[DeepSearchChatResponseChunk]]:
        """
        Performs a deep search chat completion.

        Args:
            input_data: The input data model containing messages and parameters.

        Returns:
            If stream=False, returns a DeepSearchChatResponse object.
            If stream=True, returns an async iterator yielding DeepSearchChatResponseChunk objects.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code (4xx or 5xx).
            httpx.RequestError: For network-related errors (timeout, connection error).
            ValidationError: If the API response doesn't match the expected Pydantic model.
            Exception: For other unexpected errors.
        """
        try:
            # Use exclude_unset=True to avoid sending default values unless explicitly set
            payload = input_data.model_dump(exclude_unset=True, by_alias=True)
            logger.info(f"Sending request to {self.base_url}{self.API_ENDPOINT} with stream={input_data.stream}")
            # logger.debug(f"Request payload: {payload}") # Be cautious logging full payload if sensitive

            if input_data.stream:
                return self._stream_chat_completion(payload)
            else:
                return await self._non_stream_chat_completion(payload)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            # You might want to raise a custom exception here or re-raise
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error occurred: {e}")
            raise
        except ValidationError as e:
            logger.error(f"API response validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            raise

    async def _non_stream_chat_completion(self, payload: dict) -> DeepSearchChatResponse:
        """Handles non-streaming requests."""
        response = await self.client.post(self.API_ENDPOINT, json=payload)
        response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
        response_data = response.json()
        logger.info(f"Received non-streaming response. ID: {response_data.get('id')}")
        return DeepSearchChatResponse.model_validate(response_data)

    async def _stream_chat_completion(self, payload: dict) -> AsyncIterator[DeepSearchChatResponseChunk]:
        """Handles streaming requests."""
        async with self.client.stream("POST", self.API_ENDPOINT, json=payload) as response:
            response.raise_for_status() # Check status before starting iteration
            logger.info("Starting to stream response.")
            buffer = ""
            async for line in response.aiter_lines():
                if not line:
                    continue # Skip empty lines
                buffer += line
                # Jina API streams JSON objects separated by double newlines
                while '\
\
' in buffer:
                    chunk_str, buffer = buffer.split('\
\
', 1)
                    if chunk_str.startswith("data: "):
                        chunk_str = chunk_str[len("data: "):]
                    if chunk_str == "[DONE]":
                        logger.info("Stream finished with [DONE] message.")
                        break # End of stream marker
                    try:
                        chunk_data = json.loads(chunk_str)
                        chunk = DeepSearchChatResponseChunk.model_validate(chunk_data)
                        # logger.debug(f"Yielding chunk: {chunk.model_dump_json(exclude_none=True)}")
                        yield chunk
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON chunk: {chunk_str}")
                        # Decide how to handle malformed chunks, e.g., skip or raise
                        continue
                    except ValidationError as e:
                        logger.warning(f"Failed to validate chunk: {chunk_str} - Error: {e}")
                        continue # Skip invalid chunks
            # Process any remaining data in the buffer if needed, though unlikely with \
\
 separation
            if buffer.strip() and buffer.strip() != "[DONE]":
                 logger.warning(f"Data remaining in buffer after stream ended: {buffer}")
        logger.info("Finished streaming response.")
