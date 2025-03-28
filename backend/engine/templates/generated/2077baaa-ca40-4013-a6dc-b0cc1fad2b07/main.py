from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import logging
import os
from dotenv import load_dotenv
import asyncio

from models import DeepSearchChatInput
from api import JinaDeepSearchClient, JinaDeepSearchError

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
    service_name="jina_deepsearch",
    description="Provides access to Jina AI's DeepSearch capability, an AI agent that combines web searching, reading, and reasoning to answer complex questions. Compatible with OpenAI Chat API schema."
)

# Initialize API Client
# Ensure JINA_API_KEY is set in your environment or .env file
try:
    api_client = JinaDeepSearchClient()
except ValueError as e:
    logger.error(f"Failed to initialize JinaDeepSearchClient: {e}")
    # Exit or handle appropriately if API key is missing
    import sys
    sys.exit(f"Error: {e}")

@mcp.tool()
async def chat_completion(params: DeepSearchChatInput) -> Dict[str, Any]:
    """
    Performs a deep search and reasoning process based on a conversation history.

    It iteratively searches the web, reads content, and reasons to find the best
    answer to the user's query. Supports streaming responses (recommended).

    Args:
        params: An object containing the parameters for the chat completion,
                including messages, model, stream preference, and other options.

    Returns:
        A dictionary containing the chat completion result from Jina DeepSearch.
        If stream=true (default), this will be the final aggregated response.
        If an error occurs, returns a dictionary with an 'error' key.
    """
    logger.info(f"Received request for chat_completion tool with model: {params.model}, stream: {params.stream}")
    try:
        result = await api_client.chat_completion(params)
        logger.info(f"Successfully completed chat_completion for ID: {result.get('id', 'N/A')}")
        return result
    except JinaDeepSearchError as e:
        logger.error(f"Jina API error in chat_completion: {e.status_code} - {e.detail}")
        # Return a structured error that MCP can understand
        return {
            "error": {
                "type": "api_error",
                "status_code": e.status_code,
                "message": str(e.detail) if isinstance(e.detail, (str, dict)) else repr(e.detail),
                "source": "jina_deepsearch"
            }
        }
    except Exception as e:
        logger.exception("Unexpected error in chat_completion tool")
        return {
            "error": {
                "type": "unexpected_error",
                "message": str(e),
                "source": "mcp_server"
            }
        }

# Graceful shutdown
@mcp.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Jina DeepSearch client...")
    await api_client.close()
    logger.info("Client closed. MCP server shutting down.")

if __name__ == "__main__":
    # Example of how to run the server (adjust host/port as needed)
    # uvicorn main:mcp --host 0.0.0.0 --port 8000
    # This basic run() is for simple local testing:
    # mcp.run() # This might use default ASGI server settings

    # For production, use a proper ASGI server like uvicorn or hypercorn
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    logger.info(f"Starting Jina DeepSearch MCP server on {host}:{port}")
    uvicorn.run(mcp, host=host, port=port)
