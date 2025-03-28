import httpx
import os
import logging
import json
from typing import AsyncGenerator, Optional, Dict, Any

from models import DeepSearchChatInput, DeepSearchChatResponse, DeepSearchStreamChunk, ResponseMessage, Choice, Usage, FinishDetails

logger = logging.getLogger(__name__) 

# Custom Exceptions
class DeepSearchError(Exception):
    """Base exception for DeepSearch API errors."""
    pass

class AuthenticationError(DeepSearchError):
    """Exception raised for authentication errors (401)."""
    pass

class RateLimitError(DeepSearchError):
    """Exception raised for rate limit errors (429)."""
    pass

class InvalidRequestError(DeepSearchError):
    """Exception raised for invalid request errors (400)."""
    pass

class ServerError(DeepSearchError):
    """Exception raised for server-side errors (5xx)."""
    pass

class JinaDeepSearchClient:
    """Client for interacting with the Jina AI DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 180.0): # Increased timeout for potentially long searches
        """
        Initializes the JinaDeepSearchClient.

        Args:
            api_key: The Jina AI API key. Defaults to JINA_API_KEY environment variable.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise AuthenticationError("JINA_API_KEY not found in environment variables or provided directly.")

        self.base_url = "https://deepsearch.jina.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Ensure we accept JSON
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )

    async def _handle_error(self, response: httpx.Response):
        """Raises appropriate exceptions based on HTTP status code."""
        if response.status_code == 401:
            raise AuthenticationError(f"Authentication failed: {response.text}")
        elif response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {response.text}")
        elif response.status_code == 400:
            raise InvalidRequestError(f"Invalid request: {response.text}")
        elif response.status_code >= 500:
            raise ServerError(f"Server error ({response.status_code}): {response.text}")
        else:
            response.raise_for_status() # Raise for other 4xx errors

    async def _process_stream(self, response: httpx.Response) -> DeepSearchChatResponse:
        """
        Processes the SSE stream and aggregates the response.

        Args:
            response: The streaming HTTPX response.

        Returns:
            The aggregated DeepSearchChatResponse.
        
        Raises:
            DeepSearchError: If the stream ends unexpectedly or contains errors.
        """
        aggregated_content = ""
        final_chunk_data: Dict[str, Any] = {}
        final_usage: Optional[Usage] = None
        final_finish_details: Optional[FinishDetails] = None
        first_chunk_processed = False

        try:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        chunk = DeepSearchStreamChunk.model_validate(chunk_json)

                        if not first_chunk_processed:
                            # Store metadata from the first chunk
                            final_chunk_data = chunk.model_dump(exclude={'choices', 'usage'})
                            first_chunk_processed = True

                        if chunk.choices:
                            delta = chunk.choices[0].delta
                            if delta.content:
                                aggregated_content += delta.content
                            
                            # Capture finish_details when it appears
                            if chunk.choices[0].finish_details:
                                final_finish_details = chunk.choices[0].finish_details

                        # Usage info usually comes in the last chunk
                        if chunk.usage:
                            final_usage = chunk.usage

                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON from stream: {data_str}")
                        raise DeepSearchError(f"Invalid JSON received in stream: {data_str}")
                    except Exception as e:
                        logger.error(f"Error processing stream chunk: {e}")
                        raise DeepSearchError(f"Error processing stream chunk: {e}")
        
        except httpx.ReadTimeout:
            logger.error("Read timeout during streaming")
            raise DeepSearchError("Timeout while reading stream response.")
        except httpx.RemoteProtocolError as e:
             logger.error(f"Remote protocol error during streaming: {e}")
             raise DeepSearchError(f"Connection error during streaming: {e}")
        finally:
            await response.aclose()

        if not first_chunk_processed:
             raise DeepSearchError("Stream ended unexpectedly without receiving any data chunks.")

        # Construct the final response object
        final_message = ResponseMessage(role='assistant', content=aggregated_content)
        final_choice = Choice(
            index=0, 
            message=final_message, 
            finish_details=final_finish_details
        )
        
        # Ensure essential fields are present before creating the final response
        if 'id' not in final_chunk_data or 'created' not in final_chunk_data or 'model' not in final_chunk_data:
             raise DeepSearchError("Essential metadata (id, created, model) missing from stream chunks.")

        final_response = DeepSearchChatResponse(
            id=final_chunk_data['id'],
            object='chat.completion', # Hardcode as per OpenAI spec for aggregated response
            created=final_chunk_data['created'],
            model=final_chunk_data['model'],
            choices=[final_choice],
            usage=final_usage
        )

        return final_response

    async def chat_completion(self, params: DeepSearchChatInput) -> DeepSearchChatResponse:
        """
        Performs a deep search chat completion.

        Args:
            params: Input parameters for the chat completion.

        Returns:
            The chat completion response.
        
        Raises:
            AuthenticationError: If API key is invalid.
            RateLimitError: If rate limit is exceeded.
            InvalidRequestError: If the request payload is invalid.
            ServerError: If the Jina API encounters an error.
            DeepSearchError: For other API or processing errors.
            httpx.TimeoutException: If the request times out.
        """
        endpoint = "/v1/chat/completions"
        
        # Ensure stream is True for internal processing, even if user set it to False
        # The MCP tool expects aggregation.
        payload = params.model_dump(exclude_none=True, by_alias=True)
        payload['stream'] = True # Force streaming for aggregation

        logger.info(f"Sending request to {self.base_url}{endpoint} with model {params.model}")
        # logger.debug(f"Payload: {payload}") # Be careful logging payloads with potentially sensitive data

        try:
            async with self.client.stream("POST", endpoint, json=payload) as response:
                await self._handle_error(response) # Check status before starting stream processing
                logger.info("Stream started successfully.")
                result = await self._process_stream(response)
                logger.info("Stream processed successfully.")
                return result
                
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise
        except httpx.HTTPError as e:
            # Errors during connection or non-2xx that weren't handled by _handle_error (shouldn't happen often)
            logger.error(f"HTTP error during request: {e}")
            # Attempt to parse error response if available
            try:
                error_details = e.response.text
            except Exception:
                error_details = str(e)
            raise DeepSearchError(f"HTTP error: {error_details}") from e
        except DeepSearchError as e:
             logger.error(f"DeepSearch API or processing error: {e}")
             raise # Re-raise known API errors
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            raise DeepSearchError(f"An unexpected error occurred: {str(e)}") from e

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
