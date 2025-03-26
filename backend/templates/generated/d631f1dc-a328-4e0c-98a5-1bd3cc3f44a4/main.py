from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import httpx
import logging
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from enum import Enum

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models and client
from models import Message, DeepSearchQueryParams, DeepSearchResponse
from api import DeepSearchClient

# Initialize MCP
mcp = FastMCP("deepsearch")
client = DeepSearchClient()

@mcp.tool()
async def deepsearch_query(params: DeepSearchQueryParams) -> Dict[str, Any]:
    """
    Execute a query using DeepSearch's API, supporting iterative search and reasoning for complex questions.
    
    Args:
        params: Parameters for the DeepSearch query including messages, model, and search options
        
    Returns:
        Dictionary containing the response from DeepSearch with answer, sources, and usage info
        
    Raises:
        HTTPError: If the API request fails
        ValueError: If input validation fails
    """
    try:
        logger.info(f"Executing DeepSearch query with params: {params}")
        response = await client.query(params)
        return response.dict()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error in deepsearch_query: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in deepsearch_query: {str(e)}")
        raise

if __name__ == "__main__":
    mcp.run()