import httpx
import os
import logging
from typing import AsyncGenerator
from models import DeepSearchChatParams, ResponseChunk
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSearchClient:
    """Client for interacting with the DeepSearch API"""
    
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
        self.rate_limit_semaphore = asyncio.Semaphore(10)  # 10 requests per minute
        
    async def chat_completions(self, params: DeepSearchChatParams) -> AsyncGenerator[ResponseChunk, None]:
        """
        Execute a DeepSearch query with streaming response.
        
        Args:
            params: Parameters for the chat completion
            
        Yields:
            ResponseChunk: Streaming response chunks
        """
        async with self.rate_limit_semaphore:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = params.dict(exclude_none=True)
                url = f"{self.base_url}/chat/completions"
                
                try:
                    async with client.stream(
                        "POST",
                        url,
                        json=payload,
                        headers=self.headers
                    ) as response:
                        response.raise_for_status()
                        
                        async for chunk in response.aiter_text():
                            if chunk:
                                yield ResponseChunk(content=chunk, type="text")
                                
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                    raise
                except httpx.TimeoutError:
                    logger.error("Request timed out")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error: {str(e)}")
                    raise