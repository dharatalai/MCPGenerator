from typing import Dict, Any, Optional
import httpx
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from models import DeepSearchQueryParams, DeepSearchResponse

logger = logging.getLogger(__name__)

class DeepSearchClient:
    """
    Client for interacting with the DeepSearch API.
    Handles authentication, request formatting, and response parsing.
    """
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEARCH_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEARCH_API_KEY environment variable not set")
            
        self.base_url = "https://deepsearch.jina.ai/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.timeout = 60.0
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=self.timeout
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.HTTPStatusError)),
        reraise=True
    )
    async def query(self, params: DeepSearchQueryParams) -> DeepSearchResponse:
        """
        Execute a query against the DeepSearch API.
        
        Args:
            params: Parameters for the DeepSearch query
            
        Returns:
            Parsed response from the API
            
        Raises:
            httpx.HTTPError: If the API request fails
            ValueError: If response parsing fails
        """
        url = f"{self.base_url}/chat/completions"
        payload = params.dict(exclude_none=True)
        
        try:
            logger.info(f"Sending request to DeepSearch API: {url}")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Received response from DeepSearch: {data}")
            
            return DeepSearchResponse(
                answer=data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                visited_urls=data.get("visited_urls", []),
                usage=data.get("usage", {}),
                structured_output=data.get("structured_output")
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in DeepSearch query: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing DeepSearch response: {str(e)}")
            raise