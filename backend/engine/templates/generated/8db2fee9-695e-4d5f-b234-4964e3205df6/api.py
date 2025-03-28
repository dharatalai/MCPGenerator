import httpx
import logging
import os
from typing import Dict, Any, AsyncGenerator
from models import DeepSearchChatInput, DeepSearchChatOutput, Source, Usage

logger = logging.getLogger(__name__)

class DeepSearchAPIError(Exception):
    """Custom exception for DeepSearch API errors."""
    def __init__(self, status_code: int, error_info: Dict[str, Any]):
        self.status_code = status_code
        self.error_info = error_info
        super().__init__(f"DeepSearch API Error {status_code}: {error_info}")

class DeepSearchAPIClient:
    """Asynchronous client for interacting with the Jina AI DeepSearch API."""

    DEFAULT_BASE_URL = "https://api.jina.ai/v1"
    CHAT_COMPLETIONS_ENDPOINT = "/chat/completions"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 120.0):
        """
        Initializes the DeepSearchAPIClient.

        Args:
            api_key: The Jina AI API key. Defaults to JINA_API_KEY environment variable.
            base_url: The base URL for the DeepSearch API. Defaults to https://api.jina.ai/v1.
            timeout: Default timeout for API requests in seconds.
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key not provided. Set JINA_API_KEY environment variable or pass it during initialization.")

        self.base_url = base_url or self.DEFAULT_BASE_URL
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

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the API."""
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            return response.json()
        except httpx.HTTPStatusError as e:
            error_info = e.response.json() if e.response.content else {"error": "Unknown API error"}
            logger.error(f"HTTP error {e.response.status_code} calling {e.request.url}: {error_info}")
            raise DeepSearchAPIError(status_code=e.response.status_code, error_info=error_info) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out calling {e.request.url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error calling {e.request.url}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    async def chat_completion(self, params: DeepSearchChatInput) -> DeepSearchChatOutput:
        """
        Initiates a DeepSearch chat completion process.

        Args:
            params: The input parameters including the message history.

        Returns:
            The processed response including the answer, sources, and usage.

        Raises:
            DeepSearchAPIError: If the API returns an error.
            httpx.TimeoutException: If the request times out.
            httpx.RequestError: For other network-related errors.
        """
        payload = params.dict(exclude_unset=True)
        # Ensure the model is set, Jina typically uses 'jina-deepsearch'
        if 'model' not in payload:
             payload['model'] = 'jina-deepsearch'

        # The API expects content as a string or list of dicts, Pydantic handles serialization
        # Ensure messages are serialized correctly
        serialized_messages = []
        for msg in params.messages:
            msg_dict = msg.dict(exclude_unset=True)
            if isinstance(msg.content, list):
                # Ensure content items are dicts
                msg_dict['content'] = [item.dict() for item in msg.content]
            serialized_messages.append(msg_dict)
        payload['messages'] = serialized_messages

        logger.info(f"Sending chat completion request to DeepSearch API with {len(params.messages)} messages.")

        # Note: Streaming is handled differently. This implementation assumes non-streaming
        # or that the MCP framework doesn't require explicit generator handling here.
        # If streaming is True, the API might return a stream, which needs specific handling.
        # For simplicity, we'll assume the API returns the full response even if stream=True,
        # or we only process the final result in this non-streaming client method.
        if params.stream:
            logger.warning("Streaming requested, but this client method currently processes the final aggregated response.")
            # To implement streaming properly, this method should return an AsyncGenerator
            # and handle the server-sent events (SSE) from the API.

        response_data = await self._request("POST", self.CHAT_COMPLETIONS_ENDPOINT, json=payload)

        # --- Response Parsing --- 
        # Extract data according to Jina's OpenAI-compatible schema + extensions
        try:
            answer = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Sources might be in a custom field or potentially metadata. Adjust as needed.
            # Assuming sources are provided in a top-level 'sources' key or similar.
            # This is an assumption - check Jina's exact response structure.
            raw_sources = response_data.get("sources", []) 
            if not raw_sources and isinstance(response_data.get("choices", [{}])[0].get("message", {}).get("context"), dict):
                 # Fallback: Check if sources are nested under message.context (example structure)
                 raw_sources = response_data["choices"][0]["message"]["context"].get("sources", [])
            
            sources = [Source(**source_data) for source_data in raw_sources if isinstance(source_data, dict)]

            usage_data = response_data.get("usage")
            usage = Usage(**usage_data) if usage_data else None

            return DeepSearchChatOutput(
                answer=answer,
                sources=sources,
                usage=usage,
                # Pass through other standard OpenAI fields
                id=response_data.get("id"),
                object=response_data.get("object"),
                created=response_data.get("created"),
                model=response_data.get("model"),
                system_fingerprint=response_data.get("system_fingerprint"),
                finish_reason=response_data.get("choices", [{}])[0].get("finish_reason")
            )
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing DeepSearch response: {e}. Response data: {response_data}")
            raise ValueError(f"Failed to parse essential fields from DeepSearch API response: {e}") from e
