from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Any, Generator, Optional
from pydantic import BaseModel, Field
import httpx
import logging
import os
from dotenv import load_dotenv
from models import Message, DeepSearchChatParams, ResponseChunk
from api import DeepSearchClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP
mcp = FastMCP("deepsearch-service")
api_client = DeepSearchClient()

@mcp.tool()
async def deepsearch_chat_completions(
    model: str = "jina-deepsearch-v1",
    messages: List[Message] = None,
    stream: bool = True,
    reasoning_effort: str = "medium",
    budget_tokens: Optional[int] = None,
    max_attempts: Optional[int] = None,
    no_direct_answer: bool = False,
    max_returned_urls: Optional[int] = None,
    structured_output: bool = False,
    good_domains: Optional[List[str]] = None,
    bad_domains: Optional[List[str]] = None,
    only_domains: Optional[List[str]] = None
) -> Generator[ResponseChunk, None, None]:
    """
    Execute a DeepSearch query to find the best answer through iterative search and reasoning.
    
    Args:
        model: ID of the model to use
        messages: List of messages between the user and the assistant
        stream: Whether to enable streaming of results
        reasoning_effort: Level of reasoning effort (low, medium, high)
        budget_tokens: Maximum number of tokens allowed for the process
        max_attempts: Maximum number of retries for solving the problem
        no_direct_answer: Force the model to take further thinking steps
        max_returned_urls: Maximum number of URLs to include in the final answer
        structured_output: Enable Structured Outputs
        good_domains: List of domains to prioritize
        bad_domains: List of domains to exclude
        only_domains: List of domains to exclusively include
        
    Yields:
        ResponseChunk: Streaming response containing intermediate and final results
    """
    try:
        params = DeepSearchChatParams(
            model=model,
            messages=messages,
            stream=stream,
            reasoning_effort=reasoning_effort,
            budget_tokens=budget_tokens,
            max_attempts=max_attempts,
            no_direct_answer=no_direct_answer,
            max_returned_urls=max_returned_urls,
            structured_output=structured_output,
            good_domains=good_domains,
            bad_domains=bad_domains,
            only_domains=only_domains
        )
        
        async for chunk in api_client.chat_completions(params):
            yield chunk
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.TimeoutError:
        logger.error("Request timed out")
        raise HTTPException(status_code=408, detail="Request timed out")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    mcp.run()