from mcp.server.fastmcp import FastMCP
from typing import Union, AsyncGenerator
import logging
import os
from dotenv import load_dotenv

from models import DeepSearchChatInput, DeepSearchChatResponse, DeepSearchChatChunk
from client import DeepSearchClient, DeepSearchError, AuthenticationError, InvalidRequestError, RateLimitError, ServerError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="deepsearch",
    description="MCP service for interacting with the Jina AI DeepSearch API. DeepSearch combines web searching, reading, and reasoning for comprehensive investigation."
)

# Initialize DeepSearch API Client
try:
    deepsearch_client = DeepSearchClient()
    logger.info("DeepSearchClient initialized successfully.")
except AuthenticationError as e:
    logger.error(f"Authentication Error: {e}. Please check your JINA_API_KEY.")
    # Exit or prevent server start if auth fails critically
    # For now, we'll let it proceed but tools will fail.
    deepsearch_client = None # Indicate client is not usable
except Exception as e:
    logger.exception(f"Failed to initialize DeepSearchClient: {e}")
    deepsearch_client = None

@mcp.tool()
async def chat_completion(input_data: DeepSearchChatInput) -> Union[DeepSearchChatResponse, AsyncGenerator[DeepSearchChatChunk, None]]:
    """
    Performs a deep search and reasoning process based on a conversation history using the Jina AI DeepSearch API.

    Takes user queries, searches the web, reads relevant content, and iteratively reasons to find the best answer.
    Supports streaming responses, domain filtering, and control over reasoning effort.

    Args:
        input_data: An object containing the parameters for the chat completion request, including messages, model, stream flag, and other options.

    Returns:
        If stream=False in input_data, returns a single DeepSearchChatResponse object containing the final answer, usage statistics, and visited URLs.
        If stream=True in input_data, returns an async generator yielding DeepSearchChatChunk objects, where the final chunk contains the full answer and usage details.

    Raises:
        MCP specific errors based on client exceptions (e.g., AuthenticationError, RateLimitError, etc.)
    """
    if not deepsearch_client:
        logger.error("DeepSearchClient is not initialized. Cannot process request.")
        # FastMCP typically handles raising exceptions, converting them to MCP errors
        raise ConnectionError("DeepSearch client is not available due to initialization failure.")

    logger.info(f"Received chat_completion request: stream={input_data.stream}")
    try:
        result = await deepsearch_client.chat_completion(input_data)
        logger.info(f"Successfully initiated/completed chat_completion request for stream={input_data.stream}")
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        raise # Re-raise for FastMCP to handle
    except InvalidRequestError as e:
        logger.error(f"Invalid request: {e}")
        raise # Re-raise
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        raise # Re-raise
    except ServerError as e:
        logger.error(f"DeepSearch server error: {e}")
        raise # Re-raise
    except DeepSearchError as e:
        logger.error(f"DeepSearch client error: {e}")
        raise # Re-raise
    except Exception as e:
        logger.exception(f"An unexpected error occurred in chat_completion tool: {e}")
        raise # Re-raise

if __name__ == "__main__":
    # This allows running the server directly using Uvicorn
    # Example: uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
    # The FastMCP's run() method might start its own server or provide instructions.
    # Check FastMCP documentation for the preferred way to run.
    # For development, using uvicorn is common:
    import uvicorn
    logger.info("Starting MCP server with Uvicorn...")
    # Make sure the app object is accessible if FastMCP doesn't provide a run command
    # Assuming FastMCP exposes an ASGI app instance, e.g., mcp.app
    # If not, adjust according to FastMCP's usage guide.
    # uvicorn.run("main:mcp", host="0.0.0.0", port=8000, reload=True) # Adjust if 'mcp' is not the ASGI app

    # If FastMCP has its own run method:
    mcp.run() # This might block and start the server
