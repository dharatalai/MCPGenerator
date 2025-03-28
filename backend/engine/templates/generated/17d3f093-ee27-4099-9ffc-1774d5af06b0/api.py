import httpx
import os
import logging
import json
import asyncio
from typing import Dict, Any, AsyncGenerator

from models import ChatCompletionParams, ChatCompletionResponse, Message

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 180.0  # seconds, adjust as needed for potentially long searches
DEFAULT_API_BASE_URL = "https://deepsearch.jina.ai/v1"

class DeepSearchAPIError(Exception):
    """Custom exception for DeepSearch API errors."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")

class DeepSearchAPIClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_API_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        """
        Initializes the DeepSearchAPIClient.

        Args:
            api_key: The Jina API Key. Reads from JINA_API_KEY env var if not provided.
            base_url: The base URL for the DeepSearch API.
            timeout: Default request timeout in seconds.

        Raises:
            ValueError: If the API key is not provided and not found in environment variables.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API Key not provided or found in JINA_API_KEY environment variable.")

        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Expect JSON response for non-streaming
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )
        logger.info(f"DeepSearchAPIClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Makes an HTTP request to the API."""
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
            return response
        except httpx.HTTPStatusError as e:
            # Attempt to parse error details from response body
            error_message = f"HTTP error: {e.response.status_code} {e.response.reason_phrase}"
            try:
                error_details = e.response.json()
                if isinstance(error_details, dict) and 'error' in error_details:
                     # Standard OpenAI-like error format
                     err_data = error_details['error']
                     msg = err_data.get('message', 'No details provided.')
                     typ = err_data.get('type', 'API Error')
                     error_message = f"{typ}: {msg}"
                elif isinstance(error_details, dict) and 'detail' in error_details:
                     # FastAPI-like error format
                     error_message = f"Detail: {error_details['detail']}"
                else:
                     error_message += f" | Response: {e.response.text[:500]}" # Limit response size
            except Exception:
                 error_message += f" | Response: {e.response.text[:500]}"

            logger.error(f"API request failed: {error_message} for {method} {endpoint}")
            raise DeepSearchAPIError(status_code=e.response.status_code, message=error_message) from e
        except httpx.TimeoutException as e:
            logger.error(f"API request timed out: {e} for {method} {endpoint}")
            raise asyncio.TimeoutError(f"Request timed out after {self.client.timeout.read} seconds") from e
        except httpx.RequestError as e:
            logger.error(f"API request error: {e} for {method} {endpoint}")
            raise DeepSearchAPIError(status_code=500, message=f"Request failed: {str(e)}") from e

    async def _aggregate_stream(self, response: httpx.Response) -> Dict[str, Any]:
        """Aggregates chunks from a streaming Server-Sent Events (SSE) response."""
        aggregated_content = ""
        final_response_chunk = None
        choices_data = {} # Store content deltas per choice index

        try:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        logger.info("Stream finished with [DONE] marker.")
                        break
                    try:
                        chunk = json.loads(data_str)
                        final_response_chunk = chunk # Keep track of the last chunk for metadata

                        if chunk.get('choices'):
                            delta = chunk['choices'][0].get('delta', {})
                            content_part = delta.get('content')
                            if content_part:
                                choice_index = chunk['choices'][0].get('index', 0)
                                if choice_index not in choices_data:
                                    choices_data[choice_index] = ""
                                choices_data[choice_index] += content_part
                                # logger.debug(f"Received content chunk: {content_part}")

                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON from SSE data: {data_str}")
                    except Exception as e:
                        logger.error(f"Error processing SSE chunk: {e} | Data: {data_str}")
                        # Decide whether to continue or raise
                        # raise # Re-raise might be too strict for minor chunk errors

        except httpx.RemoteProtocolError as e:
             logger.error(f"Remote protocol error during streaming: {e}")
             raise DeepSearchAPIError(status_code=502, message=f"Streaming connection error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during stream aggregation: {e}")
            raise DeepSearchAPIError(status_code=500, message=f"Failed during stream processing: {str(e)}")
        finally:
            await response.aclose()

        if not final_response_chunk:
            logger.error("Stream ended unexpectedly or no valid data received.")
            raise DeepSearchAPIError(status_code=500, message="Stream ended without valid data or [DONE] marker.")

        # Construct the final response structure based on aggregated data and the last chunk
        final_response = final_response_chunk.copy()
        if 'choices' in final_response and final_response['choices']:
            # Update choices with aggregated content
            for i, choice in enumerate(final_response['choices']):
                if i in choices_data:
                    # Assuming the structure has message.content
                    if 'message' not in choice:
                        choice['message'] = {'role': 'assistant', 'content': choices_data[i]}
                    else:
                        choice['message']['content'] = choices_data[i]
                    # Clear delta if it exists in the final structure
                    choice.pop('delta', None)
        else:
             # Handle cases where no choices were received or structure is different
             logger.warning("No choices found in the final stream chunk. Constructing basic response.")
             # Create a minimal choice structure if possible
             if choices_data:
                 final_response['choices'] = [
                     {
                         'index': idx,
                         'message': {'role': 'assistant', 'content': content},
                         'finish_reason': final_response.get('choices', [{}])[0].get('finish_reason', 'unknown') # Best guess
                     }
                     for idx, content in choices_data.items()
                 ]
             else:
                  # If no content was aggregated at all
                  final_response['choices'] = [
                     {
                         'index': 0,
                         'message': {'role': 'assistant', 'content': ''},
                         'finish_reason': 'error'
                     }
                 ]

        # Ensure essential fields are present from the last chunk
        final_response.setdefault('id', 'streamed-' + final_response.get('id', 'unknown'))
        final_response.setdefault('object', 'chat.completion')
        final_response.setdefault('created', final_response.get('created', 0))
        final_response.setdefault('model', final_response.get('model', 'unknown'))

        logger.info(f"Stream aggregated successfully for ID: {final_response.get('id')}")
        return final_response

    async def chat_completion(self, params: ChatCompletionParams) -> Dict[str, Any]:
        """
        Performs a chat completion request, handling streaming and aggregation.

        Args:
            params: The parameters for the chat completion.

        Returns:
            A dictionary representing the aggregated ChatCompletionResponse.

        Raises:
            DeepSearchAPIError: If the API returns an error.
            asyncio.TimeoutError: If the request times out.
        """
        endpoint = "/chat/completions"
        # Use model_dump to serialize Pydantic model, excluding None values
        payload = params.model_dump(exclude_none=True, by_alias=True)

        logger.debug(f"Sending chat completion request to {endpoint} with payload: {payload}")

        if params.stream:
            # Make a streaming request
            headers = self.headers.copy()
            headers['Accept'] = 'text/event-stream'
            try:
                response = await self.client.stream(
                    "POST",
                    endpoint,
                    json=payload,
                    headers=headers
                )
                # Check status *before* starting iteration for immediate errors
                if response.status_code >= 400:
                     # Try to read body for error details, then raise
                     error_body = await response.aread()
                     response.raise_for_status() # This will likely raise based on status

                # Aggregate the stream
                aggregated_data = await self._aggregate_stream(response)
                return aggregated_data
            except httpx.HTTPStatusError as e:
                # Handle errors that occur before or during stream setup
                error_message = f"HTTP error during stream setup: {e.response.status_code} {e.response.reason_phrase}"
                try:
                    error_details = json.loads(e.response.text)
                    if isinstance(error_details, dict) and 'error' in error_details:
                        err_data = error_details['error']
                        msg = err_data.get('message', 'No details provided.')
                        typ = err_data.get('type', 'API Error')
                        error_message = f"{typ}: {msg}"
                    elif isinstance(error_details, dict) and 'detail' in error_details:
                        error_message = f"Detail: {error_details['detail']}"
                    else:
                        error_message += f" | Response: {e.response.text[:500]}"
                except Exception:
                    error_message += f" | Response: {e.response.text[:500]}"
                logger.error(f"API stream request failed: {error_message}")
                raise DeepSearchAPIError(status_code=e.response.status_code, message=error_message) from e
            except (httpx.TimeoutException, httpx.RequestError, DeepSearchAPIError, asyncio.TimeoutError) as e:
                # Re-raise known errors from lower levels or stream aggregation
                raise e
            except Exception as e:
                logger.exception(f"Unexpected error during streaming request: {e}")
                raise DeepSearchAPIError(status_code=500, message=f"Unexpected streaming error: {str(e)}") from e
        else:
            # Make a regular, non-streaming request
            response = await self._request("POST", endpoint, json=payload)
            logger.info(f"Received non-streaming response for chat completion.")
            return response.json()

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("DeepSearchAPIClient closed.")
