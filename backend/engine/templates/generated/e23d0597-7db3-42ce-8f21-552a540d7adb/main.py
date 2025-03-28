import os
import logging
import json
from typing import AsyncGenerator, Union

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import httpx

from models import DeepSearchChatParams, DeepSearchChatResponse, DeepSearchChatChunk, MCPErrorResponse
from client import DeepSearchClient, DeepSearchApiError

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialization ---
SERVICE_NAME = "DeepSearch"
mcp = FastMCP(SERVICE_NAME)

# Initialize the DeepSearch API client
api_key = os.getenv("JINA_API_KEY")
deepsearch_client = DeepSearchClient(api_key=api_key)

# --- MCP Tool Definition ---
@mcp.tool()
async def chat_completion(params: DeepSearchChatParams) -> Union[DeepSearchChatResponse, AsyncGenerator[DeepSearchChatChunk, None], MCPErrorResponse]:
    """Performs a deep search and reasoning process based on a conversation history.

    This tool sends messages to the DeepSearch API, which then iteratively searches
    the web, reads content, and reasons to find the best possible answer within its
    operational constraints (like token budget or reasoning effort).

    Args:
        params: Parameters for the DeepSearch chat completion request, including messages,
                model, streaming preference, and other options.

    Returns:
        If stream=False, returns a DeepSearchChatResponse object with the complete answer.
        If stream=True, returns an AsyncGenerator yielding DeepSearchChatChunk objects.
        Returns an MCPErrorResponse if an API error occurs.
    """
    logger.info(f"Received chat_completion request with stream={params.stream}")
    try:
        if params.stream:
            logger.info("Initiating streaming chat completion.")
            # The client returns an async generator, which FastMCP handles correctly
            return deepsearch_client.chat_completion_stream(params)
        else:
            logger.info("Initiating non-streaming chat completion.")
            response = await deepsearch_client.chat_completion_no_stream(params)
            logger.info("Non-streaming chat completion successful.")
            return response

    except DeepSearchApiError as e:
        logger.error(f"DeepSearch API Error: {e.status_code} - {e.detail}", exc_info=True)
        return MCPErrorResponse(error=f"DeepSearch API Error: {e.status_code} - {e.detail}")
    except httpx.TimeoutException as e:
        logger.error(f"Request timed out: {e}", exc_info=True)
        # This is more likely if stream=False for long requests
        error_msg = "Request to DeepSearch API timed out."
        if not params.stream:
            error_msg += " Consider setting stream=True for long-running requests."
        return MCPErrorResponse(error=error_msg)
    except httpx.RequestError as e:
        logger.error(f"HTTP Request Error: {e}", exc_info=True)
        return MCPErrorResponse(error=f"HTTP Request Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return MCPErrorResponse(error=f"An unexpected error occurred: {str(e)}")

# --- Server Execution ---
if __name__ == "__main__":
    # Recommended: Run with Uvicorn for production
    # uvicorn main:mcp --host 0.0.0.0 --port 8000
    logger.info(f"Starting {SERVICE_NAME} MCP Server")
    mcp.run() # Uses default Uvicorn settings for development
