import httpx
import json
import logging
import os
from typing import Optional, AsyncGenerator, Dict, Any

from models import (
    DeepSearchChatInput,
    DeepSearchChatResponse,
    StreamChunk,
    ResponseMessage,
    ResponseChoice,
    UsageStats
)

logger = logging.getLogger(__name__)

# Define a custom exception for API errors
class DeepSearchAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")

class DeepSearchClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    DEFAULT_BASE_URL = "https://deepsearch.jina.ai/v1"
    DEFAULT_TIMEOUT = 180.0  # seconds, increased for potentially long searches
    # Rate limit info (for reference, not strictly enforced by client)
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_PERIOD = "per_minute"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("JINA_API_KEY is required. Pass it to the constructor or set the environment variable.")

        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Explicitly accept JSON for non-streamed
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
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """Makes an HTTP request to the DeepSearch API."""
        url = f"{self.base_url}{endpoint}"
        try:
            if stream:
                # For streaming, we need to handle SSE
                self.headers["Accept"] = "text/event-stream"
                req = self.client.build_request(method, endpoint, json=payload)
                response_stream = await self.client.send(req, stream=True)
                response_stream.raise_for_status() # Raise HTTP errors before streaming
                return self._process_stream(response_stream)
            else:
                self.headers["Accept"] = "application/json"
                response = await self.client.request(method, endpoint, json=payload)
                response.raise_for_status() # Raise HTTP errors (4xx, 5xx)
                return response.json()

        except httpx.HTTPStatusError as e:
            # Attempt to parse error details from response body
            error_message = f"HTTP error occurred: {e.response.status_code} {e.response.reason_phrase}"
            try:
                error_details = e.response.json()
                if isinstance(error_details, dict) and 'error' in error_details:
                    if isinstance(error_details['error'], dict) and 'message' in error_details['error']:
                        error_message = error_details['error']['message']
                    elif isinstance(error_details['error'], str):
                         error_message = error_details['error']
                elif isinstance(error_details, dict) and 'detail' in error_details:\ # Handle FastAPI validation errors etc.
                    error_message = str(error_details['detail'])
                logger.error(f"API Error Response Body: {error_details}")
            except json.JSONDecodeError:
                error_message = f"{error_message}. Response body: {e.response.text[:500]}" # Log first 500 chars

            logger.error(f"HTTP Status Error: {e.request.method} {e.request.url} - Status {e.response.status_code} - Message: {error_message}")
            raise DeepSearchAPIError(status_code=e.response.status_code, message=error_message) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e.request.method} {e.request.url}")
            raise # Re-raise timeout to be handled by caller
        except httpx.RequestError as e:
            logger.error(f"Request error: {e.request.method} {e.request.url} - {e}")
            raise DeepSearchAPIError(status_code=500, message=f"Request failed: {e}") from e
        except Exception as e:
            logger.exception(f"Unexpected error during API request to {url}")
            raise DeepSearchAPIError(status_code=500, message=f"An unexpected error occurred: {str(e)}") from e

    async def _process_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """Processes the SSE stream from the API."""
        async for line in response.aiter_lines():
            if line.startswith('data: '):
                data_content = line[len('data: '):].strip()
                if data_content == "[DONE]":
                    logger.info("Stream finished with [DONE] marker.")
                    break
                if data_content:
                    yield data_content
            elif line.strip(): # Log other non-empty lines if needed
                logger.debug(f"Received non-data line in stream: {line}")
        # Ensure the response is closed
        await response.aclose()

    async def _aggregate_streamed_response(self, stream_generator: AsyncGenerator[str, None]) -> DeepSearchChatResponse:
        """Aggregates chunks from a stream into a final response object."""
        final_response_data = {}
        aggregated_content = ""
        final_choice = None
        usage_stats = None
        deepsearch_meta = {}

        try:
            async for data_json_str in stream_generator:
                try:
                    chunk_data = json.loads(data_json_str)
                    chunk = StreamChunk.parse_obj(chunk_data)

                    # Store initial metadata (id, model, created, etc.) from the first chunk
                    if not final_response_data:
                        final_response_data = {
                            "id": chunk.id,
                            "object": "chat.completion", # Final object type
                            "created": chunk.created,
                            "model": chunk.model,
                            "system_fingerprint": chunk.system_fingerprint
                        }

                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            aggregated_content += delta.content
                        # Capture the finish reason and final choice structure
                        if chunk.choices[0].finish_reason:
                            final_choice = ResponseChoice(
                                index=chunk.choices[0].index,
                                message=ResponseMessage(role='assistant', content=aggregated_content),
                                finish_reason=chunk.choices[0].finish_reason
                            )

                    # Capture usage and DeepSearch metadata (often in the last chunk)
                    if chunk.usage:
                        usage_stats = UsageStats.parse_obj(chunk.usage)
                    if chunk.visitedURLs is not None:
                        deepsearch_meta['visitedURLs'] = chunk.visitedURLs
                    if chunk.readURLs is not None:
                        deepsearch_meta['readURLs'] = chunk.readURLs
                    if chunk.numURLs is not None:
                        deepsearch_meta['numURLs'] = chunk.numURLs

                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from stream chunk: {data_json_str}")
                    continue # Skip malformed chunks
                except Exception as e:
                    logger.exception(f"Error processing stream chunk: {chunk_data}")
                    continue # Skip problematic chunks

            if not final_response_data:
                 raise DeepSearchAPIError(status_code=500, message="Stream ended unexpectedly without yielding data.")

            # Assemble the final response
            if not final_choice:
                # If stream ended without a finish_reason, construct a basic choice
                logger.warning("Stream ended without a finish_reason. Assembling partial response.")
                final_choice = ResponseChoice(
                    index=0,
                    message=ResponseMessage(role='assistant', content=aggregated_content),
                    finish_reason='unknown' # Indicate potential truncation or error
                )
            else:
                 # Ensure the aggregated content is in the final choice message
                 final_choice.message.content = aggregated_content

            final_response_data['choices'] = [final_choice]
            if usage_stats:
                final_response_data['usage'] = usage_stats
            final_response_data.update(deepsearch_meta)

            return DeepSearchChatResponse.parse_obj(final_response_data)

        except DeepSearchAPIError: # Propagate API errors immediately
            raise
        except Exception as e:
            logger.exception("Error during stream aggregation")
            raise DeepSearchAPIError(status_code=500, message=f"Failed to aggregate stream: {str(e)}") from e

    async def chat_completion(self, params: DeepSearchChatInput) -> DeepSearchChatResponse:
        """Sends a chat completion request to the DeepSearch API.

        Handles both streaming and non-streaming requests.
        For streaming requests, aggregates the response chunks.
        "
        endpoint = "/chat/completions"
        # Convert Pydantic model to dict, excluding None values for clean payload
        payload = params.dict(exclude_none=True)

        if params.stream:
            logger.info(f"Initiating streamed chat completion request to {endpoint}")
            stream_generator = await self._request(method="POST", endpoint=endpoint, payload=payload, stream=True)
            # Type hint check
            if not isinstance(stream_generator, AsyncGenerator):
                 raise TypeError("Expected AsyncGenerator from _request for streaming.")
            aggregated_response = await self._aggregate_streamed_response(stream_generator)
            return aggregated_response
        else:
            logger.info(f"Initiating non-streamed chat completion request to {endpoint}")
            response_data = await self._request(method="POST", endpoint=endpoint, payload=payload, stream=False)
            # Type hint check
            if not isinstance(response_data, dict):
                 raise TypeError("Expected dict from _request for non-streaming.")
            return DeepSearchChatResponse.parse_obj(response_data)
