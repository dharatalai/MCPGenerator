import httpx
import os
import logging
import json
import asyncio
from typing import AsyncGenerator, Union, Optional, Dict, Any
from pydantic import ValidationError

from models import DeepSearchChatInput, DeepSearchChatResponse, DeepSearchChatChunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default base URL for the DeepSearch API
DEFAULT_DEEPSEARCH_API_BASE_URL = "https://deepsearch.jina.ai"

class DeepSearchError(Exception):
    """Base exception for DeepSearch client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class AuthenticationError(DeepSearchError):
    """Exception for authentication errors (401)."""
    pass

class InvalidRequestError(DeepSearchError):
    """Exception for invalid request errors (400)."""
    pass

class RateLimitError(DeepSearchError):
    """Exception for rate limit errors (429)."""
    pass

class ServerError(DeepSearchError):
    """Exception for server-side errors (5xx)."""
    pass

class DeepSearchClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 120.0):
        """
        Initializes the DeepSearchClient.

        Args:
            api_key: Jina AI API key. Defaults to JINA_API_KEY environment variable.
            base_url: Base URL for the DeepSearch API. Defaults to https://deepsearch.jina.ai.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise AuthenticationError("JINA_API_KEY not provided or found in environment variables.")

        self.base_url = base_url or os.getenv("DEEPSEARCH_API_BASE_URL", DEFAULT_DEEPSEARCH_API_BASE_URL)
        self.endpoint = "/v1/chat/completions"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )

    async def _request(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[httpx.Response, AsyncGenerator[str, None]]:
        """Makes an HTTP request to the DeepSearch API."""
        try:
            if stream:
                # For streaming, we need to handle the response differently
                req = self.client.build_request(method, url, json=json_data)
                response_stream = await self.client.send(req, stream=True)
                # Raise status errors early for the initial connection
                response_stream.raise_for_status()
                return self._process_stream(response_stream)
            else:
                response = await self.client.request(method, url, json=json_data)
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
                return response

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                response_data = e.response.json()
            except json.JSONDecodeError:
                response_data = {"error": e.response.text or "Unknown error"}
            
            error_message = f"HTTP error {status_code}: {response_data.get('error', {}).get('message', str(e))}"
            logger.error(f"{error_message} - URL: {e.request.url}")
            
            if status_code == 401:
                raise AuthenticationError(error_message, status_code, response_data) from e
            elif status_code == 400:
                 raise InvalidRequestError(error_message, status_code, response_data) from e
            elif status_code == 429:
                raise RateLimitError(error_message, status_code, response_data) from e
            elif 500 <= status_code < 600:
                 raise ServerError(error_message, status_code, response_data) from e
            else:
                raise DeepSearchError(error_message, status_code, response_data) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise DeepSearchError(f"Request timed out after {self.client.timeout.read}s", status_code=408) from e
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
            raise DeepSearchError(f"Request error: {e}") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            raise DeepSearchError(f"An unexpected error occurred: {str(e)}") from e

    async def _process_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """Processes the streaming response (Server-Sent Events)."""
        buffer = ""
        async for line in response.aiter_lines():
            if not line:
                # Empty line indicates end of an event
                if buffer.startswith("data:"):
                    data_str = buffer[len("data:"):].strip()
                    if data_str == "[DONE]":
                        logger.info("Stream finished with [DONE] message.")
                        break
                    try:
                        # Yield the raw JSON string data part
                        yield data_str
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON from stream chunk: {data_str}")
                buffer = ""
            else:
                buffer += line + "\
" # Rebuild multi-line events if any
        # Ensure the stream is closed
        await response.aclose()

    async def chat_completion(
        self,
        input_data: DeepSearchChatInput
    ) -> Union[DeepSearchChatResponse, AsyncGenerator[DeepSearchChatChunk, None]]:
        """
        Performs a deep search chat completion.

        Args:
            input_data: The input parameters for the chat completion.

        Returns:
            If stream=False, returns a DeepSearchChatResponse object.
            If stream=True, returns an async generator yielding DeepSearchChatChunk objects.

        Raises:
            AuthenticationError: If the API key is invalid.
            InvalidRequestError: If the request payload is invalid.
            RateLimitError: If the rate limit is exceeded.
            ServerError: If the server encounters an error.
            DeepSearchError: For other client or connection errors.
            ValidationError: If the response data doesn't match the Pydantic model.
        """
        payload = input_data.dict(exclude_none=True)
        stream = input_data.stream

        logger.info(f"Sending request to DeepSearch API: stream={stream}")
        # logger.debug(f"Payload: {payload}") # Be cautious logging sensitive data

        response_or_stream = await self._request(
            method="POST",
            url=self.endpoint,
            json_data=payload,
            stream=stream
        )

        if stream:
            # We expect an async generator of raw JSON strings here
            if not isinstance(response_or_stream, AsyncGenerator):
                 raise DeepSearchError("Expected an async generator for streaming response, but got something else.")
            return self._parse_stream_chunks(response_or_stream)
        else:
            # We expect an httpx.Response object here
            if not isinstance(response_or_stream, httpx.Response):
                 raise DeepSearchError("Expected an httpx.Response for non-streaming response, but got something else.")
            try:
                response_json = response_or_stream.json()
                logger.info("Received non-streaming response from DeepSearch API.")
                # logger.debug(f"Response JSON: {response_json}")
                return DeepSearchChatResponse.parse_obj(response_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {e}")
                raise DeepSearchError(f"Failed to decode JSON response: {response_or_stream.text}") from e
            except ValidationError as e:
                logger.error(f"Failed to validate response against DeepSearchChatResponse model: {e}")
                raise DeepSearchError(f"Invalid response format received: {e}") from e

    async def _parse_stream_chunks(self, stream: AsyncGenerator[str, None]) -> AsyncGenerator[DeepSearchChatChunk, None]:
        """Parses raw JSON strings from the stream into DeepSearchChatChunk objects."""
        async for chunk_str in stream:
            try:
                chunk_json = json.loads(chunk_str)
                # logger.debug(f"Received stream chunk: {chunk_json}")
                yield DeepSearchChatChunk.parse_obj(chunk_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode JSON stream chunk: {chunk_str}, error: {e}")
                # Decide whether to skip or raise. Skipping might be more robust for minor stream issues.
                continue
            except ValidationError as e:
                logger.warning(f"Failed to validate stream chunk against DeepSearchChatChunk model: {chunk_str}, error: {e}")
                # Skipping invalid chunks
                continue
            except Exception as e:
                logger.exception(f"Unexpected error processing stream chunk: {chunk_str}, error: {e}")
                # Depending on severity, you might want to raise here
                continue

# Example usage (for testing client directly)
async def main():
    load_dotenv()
    client = DeepSearchClient()
    test_input = DeepSearchChatInput(
        messages=[ChatMessage(role="user", content="What is the weather in San Francisco?")],
        stream=False # Test non-streaming first
    )
    try:
        print("--- Testing Non-Streaming --- ")
        response = await client.chat_completion(test_input)
        print(response.json(indent=2))

        print("\
--- Testing Streaming --- ")
        test_input.stream = True
        async for chunk in await client.chat_completion(test_input):
             print(chunk.json())

    except DeepSearchError as e:
        print(f"An error occurred: {e}")
        if e.response_data:
            print(f"Response data: {e.response_data}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    asyncio.run(main())
