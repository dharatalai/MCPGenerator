import httpx
import os
import logging
import json
from typing import AsyncGenerator, Dict, Any, Union
from pydantic import ValidationError

from models import DeepSearchChatInput, ChatCompletion, ChatCompletionChunk

logger = logging.getLogger(__name__) 

class JinaDeepSearchError(Exception):
    """Custom exception for Jina DeepSearch API errors."""
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")

class JinaDeepSearchClient:
    """Asynchronous client for interacting with the Jina DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://deepsearch.jina.ai/v1"):
        """
        Initializes the Jina DeepSearch API client.

        Args:
            api_key: The Jina API key. Reads from JINA_API_KEY environment variable if not provided.
            base_url: The base URL for the Jina DeepSearch API.
        
        Raises:
            ValueError: If the API key is not provided and not found in environment variables.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key not provided or found in JINA_API_KEY environment variable.")
        
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        # Increased timeout for potentially long searches, especially non-streaming
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=300.0)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def chat_completions(self, params: DeepSearchChatInput) -> Union[ChatCompletion, AsyncGenerator[ChatCompletionChunk, None]]:
        """
        Initiates a DeepSearch chat completion process.

        Args:
            params: The input parameters conforming to DeepSearchChatInput model.

        Returns:
            If stream=False, returns a ChatCompletion object.
            If stream=True, returns an async generator yielding ChatCompletionChunk objects.
        
        Raises:
            JinaDeepSearchError: For API-specific errors (4xx, 5xx).
            httpx.RequestError: For network-related issues.
            ValidationError: If the API response doesn't match the expected Pydantic model.
            Exception: For other unexpected errors.
        """
        endpoint = "/chat/completions"
        # Use model_dump to serialize Pydantic models correctly, exclude None values
        payload = params.model_dump(exclude_none=True)

        try:
            if params.stream:
                logger.info(f"Initiating streaming request to {self.base_url}{endpoint}")
                return self._stream_chat_completions(endpoint, payload)
            else:
                logger.info(f"Initiating non-streaming request to {self.base_url}{endpoint}")
                response = await self.client.post(endpoint, json=payload)
                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
                try:
                    return ChatCompletion.model_validate(response.json())
                except ValidationError as e:
                    logger.error(f"Failed to validate non-streaming response: {e}")
                    logger.debug(f"Invalid response data: {response.text}")
                    raise

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                detail = e.response.json()
            except json.JSONDecodeError:
                detail = e.response.text
            
            log_message = f"HTTP error {status_code} from Jina DeepSearch API: {detail}"
            if 400 <= status_code < 500:
                logger.warning(log_message) # Client-side errors
            else:
                logger.error(log_message) # Server-side errors
            raise JinaDeepSearchError(status_code=status_code, detail=detail) from e
        
        except httpx.RequestError as e:
            logger.error(f"Network error connecting to Jina DeepSearch API: {e}")
            raise # Re-raise network errors
        
        except Exception as e:
            logger.exception(f"An unexpected error occurred during chat completion: {e}")
            raise # Re-raise other unexpected errors

    async def _stream_chat_completions(self, endpoint: str, payload: Dict[str, Any]) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Handles the streaming response from the chat completions endpoint.
        Parses Server-Sent Events (SSE).
        """
        try:
            async with self.client.stream("POST", endpoint, json=payload) as response:
                # Check for initial errors before starting to stream
                if response.status_code >= 400:
                     error_content = await response.aread()
                     try:
                         detail = json.loads(error_content)
                     except json.JSONDecodeError:
                         detail = error_content.decode()
                     raise JinaDeepSearchError(status_code=response.status_code, detail=detail)
                
                response.raise_for_status() # Should be redundant if check above works, but good practice
                
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            logger.info("Stream finished with [DONE] marker.")
                            break
                        if data_str:
                            try:
                                chunk_data = json.loads(data_str)
                                yield ChatCompletionChunk.model_validate(chunk_data)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode JSON chunk: {data_str}")
                            except ValidationError as e:
                                logger.error(f"Failed to validate streaming chunk: {e}")
                                logger.debug(f"Invalid chunk data: {data_str}")
                                # Decide whether to raise or just log and continue
                                # raise # Option: Stop processing on validation error
                                continue # Option: Log and try to continue
                    elif line.strip(): # Log other non-empty lines if needed
                        logger.debug(f"Received non-data line: {line}")

        except httpx.HTTPStatusError as e:
            # This might catch errors that occur *during* the stream if the server sends an error status later
            status_code = e.response.status_code
            try:
                detail = e.response.json()
            except json.JSONDecodeError:
                detail = e.response.text # Or await e.response.aread() if needed
            log_message = f"HTTP error {status_code} during Jina DeepSearch stream: {detail}"
            logger.error(log_message)
            raise JinaDeepSearchError(status_code=status_code, detail=detail) from e
        
        except httpx.RequestError as e:
            logger.error(f"Network error during Jina DeepSearch stream: {e}")
            raise
        
        except Exception as e:
            logger.exception(f"An unexpected error occurred during stream processing: {e}")
            raise
