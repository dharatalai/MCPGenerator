import httpx
import logging
import os
import json
from typing import Dict, Any, AsyncGenerator

from models import DeepSearchChatInput

logger = logging.getLogger(__name__)

class JinaDeepSearchError(Exception):
    """Custom exception for Jina DeepSearch API errors."""
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Jina DeepSearch API Error {status_code}: {detail}")

class JinaDeepSearchClient:
    """Client for interacting with the Jina AI DeepSearch API."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 180.0):
        """
        Initializes the Jina DeepSearch client.

        Args:
            api_key: The Jina API key. Reads from JINA_API_KEY env var if not provided.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key not provided or found in JINA_API_KEY environment variable.")

        self.base_url = "https://deepsearch.jina.ai/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json" # Ensure we accept JSON
        }
        # Use a longer timeout as DeepSearch can take time, especially non-streaming
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )

    async def _request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes a non-streaming request to the API."""
        try:
            response = await self.client.request(method, endpoint, json=payload)
            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling Jina DeepSearch: {e.response.status_code} - {e.response.text}")
            try:
                detail = e.response.json()
            except json.JSONDecodeError:
                detail = e.response.text
            raise JinaDeepSearchError(status_code=e.response.status_code, detail=detail) from e
        except httpx.RequestError as e:
            logger.error(f"Network error calling Jina DeepSearch: {e}")
            raise JinaDeepSearchError(status_code=503, detail=f"Network error: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from Jina DeepSearch: {e}")
            raise JinaDeepSearchError(status_code=500, detail=f"Invalid JSON response: {e}") from e

    async def _stream_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Makes a streaming request to the API and yields parsed SSE events."""
        try:
            async with self.client.stream(method, endpoint, json=payload) as response:
                # Check for initial errors before starting to stream
                if response.status_code >= 400:
                    error_content = await response.aread()
                    logger.error(f"HTTP error calling Jina DeepSearch (stream init): {response.status_code} - {error_content.decode()}")
                    try:
                        detail = json.loads(error_content)
                    except json.JSONDecodeError:
                        detail = error_content.decode()
                    raise JinaDeepSearchError(status_code=response.status_code, detail=detail)

                # Process Server-Sent Events (SSE)
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while '\
\
' in buffer:
                        event_str, buffer = buffer.split('\
\
', 1)
                        if event_str.strip():
                            lines = event_str.strip().split('\
')
                            if lines and lines[0].startswith('data: '):
                                data_json = lines[0][len('data: '):].strip()
                                if data_json == "[DONE]":
                                    logger.info("Stream finished with [DONE] marker.")
                                    return # End generation
                                try:
                                    data = json.loads(data_json)
                                    yield data
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to decode stream data chunk: {data_json} - Error: {e}")
                            else:
                                logger.warning(f"Received unexpected SSE format: {event_str}")
                # Process any remaining buffer content if needed (though SSE usually ends with \
\
)
                if buffer.strip():
                     logger.warning(f"Trailing data in stream buffer: {buffer}")

        except httpx.RequestError as e:
            logger.error(f"Network error during Jina DeepSearch stream: {e}")
            raise JinaDeepSearchError(status_code=503, detail=f"Network error during stream: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during Jina DeepSearch stream processing: {e}", exc_info=True)
            raise JinaDeepSearchError(status_code=500, detail=f"Stream processing error: {e}") from e

    async def chat_completion(self, params: DeepSearchChatInput) -> Dict[str, Any]:
        """
        Performs a deep search chat completion.

        Handles both streaming and non-streaming requests based on params.stream.
        If streaming, aggregates the results into a final dictionary matching
        the expected non-streaming response structure as closely as possible.

        Args:
            params: The input parameters for the chat completion.

        Returns:
            A dictionary containing the chat completion result.

        Raises:
            JinaDeepSearchError: If the API returns an error or network issues occur.
        """
        endpoint = "chat/completions"
        # Use model_dump to serialize Pydantic model, exclude None values
        payload = params.model_dump(exclude_none=True)
        logger.info(f"Sending request to Jina DeepSearch: {endpoint} with stream={params.stream}")
        # logger.debug(f"Payload: {payload}") # Be careful logging potentially sensitive message content

        if not params.stream:
            # Non-streaming request
            try:
                result = await self._request("POST", endpoint, payload=payload)
                logger.info("Received non-streaming response from Jina DeepSearch.")
                return result
            except Exception as e:
                logger.error(f"Error in non-streaming chat completion: {e}", exc_info=True)
                raise # Re-raise the caught JinaDeepSearchError or other exceptions
        else:
            # Streaming request - aggregate results
            final_result = {
                "id": None,
                "object": "chat.completion",
                "created": None,
                "model": params.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": ""},
                        "finish_reason": None,
                        # Add potential fields for citations/annotations if needed
                        "annotations": []
                    }
                ],
                "usage": None, # Usage is often sent at the end or not at all in streams
                "_stream_chunks_processed": 0 # Internal counter
            }
            aggregated_content = ""
            try:
                async for chunk in self._stream_request("POST", endpoint, payload=payload):
                    final_result["_stream_chunks_processed"] += 1
                    # logger.debug(f"Stream chunk received: {chunk}")
                    if not final_result["id"] and chunk.get("id"):
                        final_result["id"] = chunk.get("id")
                    if not final_result["created"] and chunk.get("created"):
                        final_result["created"] = chunk.get("created")

                    if chunk.get("choices"):
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"] is not None:
                            aggregated_content += delta["content"]
                        if chunk["choices"][0].get("finish_reason"):
                            final_result["choices"][0]["finish_reason"] = chunk["choices"][0]["finish_reason"]
                        # Handle annotations if present in delta
                        if "annotations" in delta and delta["annotations"]:
                             final_result["choices"][0]["annotations"].extend(delta["annotations"])

                    # Check for usage information, often sent in the last chunk
                    if chunk.get("usage"):
                        final_result["usage"] = chunk["usage"]

                # Update the final aggregated content
                final_result["choices"][0]["message"]["content"] = aggregated_content

                if final_result["_stream_chunks_processed"] == 0:
                    logger.warning("Stream completed without receiving any data chunks.")
                    # Consider raising an error or returning a specific message
                    raise JinaDeepSearchError(status_code=500, detail="Stream ended prematurely without data.")

                logger.info(f"Aggregated streaming response from Jina DeepSearch after {final_result['_stream_chunks_processed']} chunks.")
                return final_result

            except Exception as e:
                logger.error(f"Error processing streaming chat completion: {e}", exc_info=True)
                # Ensure JinaDeepSearchError is raised for consistency
                if not isinstance(e, JinaDeepSearchError):
                    raise JinaDeepSearchError(status_code=500, detail=f"Stream processing failed: {e}") from e
                else:
                    raise # Re-raise the original JinaDeepSearchError

    async def close(self):
        """Closes the underlying HTTP client."""
        await self.client.aclose()
        logger.info("Jina DeepSearch client closed.")
