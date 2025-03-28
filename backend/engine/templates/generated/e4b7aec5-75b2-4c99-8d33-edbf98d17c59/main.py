import logging
import os
import asyncio
from typing import Union, AsyncGenerator, Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
import httpx

from models import DeepSearchChatInput, ChatCompletion, ChatCompletionChunk
from api import JinaDeepSearchClient, JinaDeepSearchError

# --- Configuration ---

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Initialization ---

SERVICE_NAME = "jina_deepsearch"
SERVICE_DESCRIPTION = "MCP server for Jina DeepSearch API. DeepSearch combines web searching, reading, and reasoning for comprehensive investigation."

# Initialize MCP Server
mcp = FastMCP(SERVICE_NAME, description=SERVICE_DESCRIPTION)

# Initialize API Client
try:
    api_client = JinaDeepSearchClient()
except ValueError as e:
    logger.critical(f"Failed to initialize JinaDeepSearchClient: {e}")
    # Decide if the application should exit or continue without a functional client
    # For this service, the client is essential, so we might exit or raise
    raise SystemExit(f"Configuration error: {e}")

# --- Tool Definition ---

@mcp.tool()
async def chat_completions(params: DeepSearchChatInput) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """
    Initiates a Jina DeepSearch process based on a conversation history.
    
    Performs iterative search, reading, and reasoning. Supports streaming 
    responses (recommended) to receive intermediate thinking steps and the 
    final answer.

    Args:
        params: Input parameters including messages, model, stream flag, and other options.

    Returns:
        If stream=False, returns a dictionary representing the ChatCompletion object.
        If stream=True, returns an async generator yielding dictionaries representing ChatCompletionChunk objects.
        Returns an error dictionary if an API or validation error occurs.
    """
    logger.info(f"Received chat_completions request. Streaming: {params.stream}")
    try:
        result = await api_client.chat_completions(params)
        
        if isinstance(result, AsyncGenerator):
            # Handle streaming response
            async def stream_wrapper():
                try:
                    async for chunk in result:
                        yield chunk.model_dump(exclude_none=True)
                except (JinaDeepSearchError, httpx.RequestError, ValidationError) as e:
                    logger.error(f"Error during stream processing in tool: {e}")
                    # Yield an error dictionary as the last item in the stream
                    yield {"error": str(e), "status_code": getattr(e, 'status_code', 500)}
                except Exception as e:
                    logger.exception(f"Unexpected error during stream processing in tool: {e}")
                    yield {"error": "An unexpected error occurred during streaming.", "status_code": 500}
            return stream_wrapper() # Return the async generator
        else:
            # Handle non-streaming response
            return result.model_dump(exclude_none=True)
            
    except (JinaDeepSearchError, httpx.RequestError, ValidationError) as e:
        logger.error(f"Error calling Jina DeepSearch API: {e}")
        # Return a dictionary indicating the error for non-streaming cases
        return {"error": str(e), "status_code": getattr(e, 'status_code', 500)}
    except Exception as e:
        logger.exception(f"An unexpected error occurred in chat_completions tool: {e}")
        return {"error": "An unexpected server error occurred.", "status_code": 500}

# --- Server Lifecycle ---

@mcp.on_event("shutdown")
async def shutdown_event():
    """Cleanly close the API client on server shutdown."""
    logger.info("Shutting down Jina DeepSearch client...")
    await api_client.close()
    logger.info("Jina DeepSearch client closed.")

# --- Run Server ---

if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} MCP server...")
    # Note: FastMCP's run() method starts the Uvicorn server.
    # Configuration like host and port can be passed to mcp.run() or set via environment variables.
    mcp.run()
