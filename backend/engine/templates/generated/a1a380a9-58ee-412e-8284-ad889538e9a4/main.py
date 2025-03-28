from mcp.server.fastmcp import FastMCP
from typing import List, Optional, Dict, Any
import logging
import os
from dotenv import load_dotenv

# Import models and API client
from models import DeepSearchChatInput, DeepSearchChatResponse, Message
from api import JinaDeepSearchClient, DeepSearchError, AuthenticationError, RateLimitError, InvalidRequestError, ServerError

# --- Configuration ---

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- MCP Server Initialization ---

mcp = FastMCP(
    service_name="jina_deepsearch",
    description="MCP service for Jina AI DeepSearch, providing iterative web search, reading, and reasoning capabilities to answer complex questions. It utilizes the Jina AI DeepSearch API, which is compatible with the OpenAI Chat API schema."
)

# --- API Client Initialization ---

try:
    api_client = JinaDeepSearchClient()
except AuthenticationError as e:
    logger.error(f"Failed to initialize JinaDeepSearchClient: {e}")
    # Allow server to start but tools will fail if client wasn't initialized
    api_client = None 
except Exception as e:
    logger.error(f"Unexpected error initializing JinaDeepSearchClient: {e}")
    api_client = None

# --- MCP Tool Definition ---

@mcp.tool(
    name="chat_completion",
    description="Performs a deep search and reasoning process based on a conversation history. It iteratively searches the web, reads content, and reasons to find the best answer to the user's query. Supports text, image (webp, png, jpeg as data URI), and document (txt, pdf as data URI) inputs in messages. Returns the final aggregated answer along with metadata.",
    input_model=DeepSearchChatInput,
    returns=DeepSearchChatResponse
)
async def chat_completion(params: DeepSearchChatInput) -> Dict[str, Any]:
    """
    MCP tool to perform Jina AI DeepSearch chat completion.

    Handles streaming internally and returns the aggregated response.

    Args:
        params: Input parameters matching the DeepSearchChatInput model.

    Returns:
        A dictionary representing the DeepSearchChatResponse or an error dictionary.
    """
    if api_client is None:
        logger.error("JinaDeepSearchClient is not initialized. Cannot process request.")
        return {"error": "Service configuration error: API client not initialized."}

    logger.info(f"Received chat_completion request with model: {params.model}")
    
    # The API client internally forces stream=True and handles aggregation.
    # We pass the user's preference for stream just in case, but it's overridden.
    # We don't need to change params.stream here.

    try:
        result: DeepSearchChatResponse = await api_client.chat_completion(params)
        logger.info(f"Successfully completed chat_completion request {result.id}")
        # Return the Pydantic model's dictionary representation
        return result.model_dump(by_alias=True, exclude_none=True)

    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return {"error": f"Authentication failed: {e}"}
    except RateLimitError as e:
        logger.warning(f"Rate limit error: {e}")
        return {"error": f"Rate limit exceeded: {e}"}
    except InvalidRequestError as e:
        logger.error(f"Invalid request error: {e}")
        return {"error": f"Invalid request: {e}"}
    except ServerError as e:
        logger.error(f"Server error: {e}")
        return {"error": f"Jina API server error: {e}"}
    except DeepSearchError as e:
        logger.error(f"DeepSearch API error: {e}")
        return {"error": f"DeepSearch API error: {e}"}
    except httpx.TimeoutException:
        logger.error("Request to Jina API timed out.")
        return {"error": "Request timed out while contacting the Jina DeepSearch API."}
    except Exception as e:
        logger.exception(f"Unexpected error in chat_completion tool: {e}") # Log full traceback
        return {"error": f"An unexpected error occurred: {str(e)}"}

# --- Server Shutdown Hook ---

@mcp.on_event("shutdown")
async def shutdown_event():
    """Cleanly closes the API client connection on server shutdown."""
    if api_client:
        logger.info("Closing Jina DeepSearch API client...")
        await api_client.close()
        logger.info("Jina DeepSearch API client closed.")
    else:
        logger.info("No API client to close.")

# --- Run Server ---

if __name__ == "__main__":
    logger.info("Starting Jina DeepSearch MCP server...")
    # Note: FastMCP's run() method handles the ASGI server setup (like uvicorn)
    mcp.run()
