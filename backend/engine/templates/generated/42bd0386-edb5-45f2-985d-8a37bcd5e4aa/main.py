from mcp.server.fastmcp import FastMCP, ToolContext
from typing import Union, AsyncGenerator
import logging
import os
from dotenv import load_dotenv
import asyncio

from models import DeepSearchChatInput, DeepSearchResponse, DeepSearchResponseChunk
from api import DeepSearchAPIClient, DeepSearchAPIError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="deepsearch",
    description="MCP interface for the Jina DeepSearch API. Provides web searching, content reading, and reasoning capabilities."
)

# Initialize API Client
# The API key is read from the JINA_API_KEY environment variable within the client
api_client = DeepSearchAPIClient()

@mcp.tool()
async def chat_completion(
    ctx: ToolContext,
    params: DeepSearchChatInput
) -> Union[DeepSearchResponse, AsyncGenerator[DeepSearchResponseChunk, None]]:
    """
    Performs a deep search and reasoning process to answer a user query based on conversational context.

    It iteratively searches the web, reads relevant content, and reasons until it finds an accurate answer
    or reaches resource limits. Supports text, image, and document inputs within messages.

    Args:
        ctx: The ToolContext provided by FastMCP.
        params: Input parameters including messages, model, streaming options, etc.

    Returns:
        If stream=False, returns a single DeepSearchResponse object.
        If stream=True, returns an async generator yielding DeepSearchResponseChunk objects.

    Raises:
        DeepSearchAPIError: If the API call fails after retries.
        Exception: For other unexpected errors during execution.
    """
    logger.info(f"Received chat_completion request (stream={params.stream})")
    try:
        # The API client handles both streaming and non-streaming responses internally
        result = await api_client.chat_completion(params)

        if isinstance(result, AsyncGenerator):
            logger.info("Streaming response back to client.")
            # If it's a generator, return it directly for FastMCP to handle streaming
            return result
        else:
            logger.info("Returning non-streaming response to client.")
            # If it's a single response object, return it
            return result

    except DeepSearchAPIError as e:
        logger.error(f"DeepSearch API error in chat_completion: {e.status_code} - {e.detail}")
        # Re-raise the specific API error to potentially inform the client
        # FastMCP might map this to a standard MCP error response
        raise
    except Exception as e:
        logger.exception("An unexpected error occurred in chat_completion tool")
        # Raise a generic exception for FastMCP to handle
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

# Graceful shutdown
@mcp.on_shutdown
async def shutdown():
    logger.info("Shutting down DeepSearch MCP server...")
    await api_client.close()
    logger.info("DeepSearch API client closed.")

if __name__ == "__main__":
    # Example of how to run (though typically you'd use uvicorn or similar)
    # mcp.run() # This uses a basic development server

    # For production, use an ASGI server like uvicorn:
    # uvicorn main:mcp.app --host 0.0.0.0 --port 8000
    logger.info("Starting DeepSearch MCP server.")
    logger.info("Run with: uvicorn main:mcp.app --host 0.0.0.0 --port <your_port>")
    # To run directly for simple testing:
    # import uvicorn
    # uvicorn.run(mcp.app, host="127.0.0.1", port=8000)
