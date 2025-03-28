from mcp.server.fastmcp import FastMCP, ToolContext
from typing import AsyncGenerator, Union, Any
import logging
import os
import asyncio
from dotenv import load_dotenv

from models import (DeepSearchChatRequest, DeepSearchChatResponse, DeepSearchChatChunk)
from api import DeepSearchApiClient

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="jina_deepsearch",
    description="MCP server for Jina AI DeepSearch, an API that combines web searching, reading, and reasoning to provide comprehensive answers to complex questions. It is designed to be compatible with the OpenAI Chat API schema."
)

# Initialize API Client
# Use a context manager approach for client lifecycle
@mcp.context_lifespan
async def api_client_lifespan(context: ToolContext):
    """Manage the lifecycle of the DeepSearchApiClient."""
    logger.info("Initializing DeepSearch API client...")
    client = DeepSearchApiClient()
    context.state.api_client = client
    try:
        yield # Server runs here
    finally:
        logger.info("Closing DeepSearch API client...")
        await client.close()

# Define MCP Tools
@mcp.tool()
async def chat_completions(
    context: ToolContext,
    request: DeepSearchChatRequest
) -> Union[DeepSearchChatResponse, AsyncGenerator[DeepSearchChatChunk, None]]:
    """"""
    Generates a response based on iterative search, reading, and reasoning using Jina DeepSearch.

    Accepts a list of messages and various parameters to control the search and reasoning process.
    Supports streaming responses.

    Args:
        context: The MCP ToolContext, providing access to shared state (like the API client).
        request: The chat completion request parameters conforming to DeepSearchChatRequest.

    Returns:
        If request.stream is False, returns a single DeepSearchChatResponse object.
        If request.stream is True, returns an async generator yielding DeepSearchChatChunk objects.

    Raises:
        Exception: Propagates exceptions from the API client (e.g., HTTP errors, validation errors).
    """"
    api_client: DeepSearchApiClient = context.state.api_client
    logger.info(f"Executing chat_completions tool (stream={request.stream})")
    try:
        result = await api_client.chat_completions(request)
        return result
    except Exception as e:
        logger.exception(f"Error executing chat_completions tool: {e}")
        # Re-raise the exception to let FastMCP handle standard error responses
        raise

# --- Main Execution --- #
if __name__ == "__main__":
    # This block is for local development/debugging if needed.
    # Production deployment should use a command like:
    # uvicorn main:mcp.app --host 0.0.0.0 --port 8000
    logger.info("Starting Jina DeepSearch MCP server locally...")

    # Example of how to run the server directly (for simple testing)
    # Note: `mcp.run()` is a simplified way, `uvicorn` is preferred for production
    # mcp.run() # This might block, consider async setup if needed here

    # To run with uvicorn programmatically (alternative):
    # import uvicorn
    # uvicorn.run(mcp.app, host="127.0.0.1", port=8000)
    
    print("MCP server defined. Run with: uvicorn main:mcp.app --reload")
