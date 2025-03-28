from mcp.server.fastmcp import FastMCP, ToolContext
from typing import Dict, Any, AsyncGenerator
import logging
import os
from dotenv import load_dotenv
import httpx
from pydantic import ValidationError
import json

from models import DeepSearchChatParams, DeepSearchChatResponse, DeepSearchChatStreamResponse
from api import DeepSearchClient

# --- Configuration ---

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- MCP Server Initialization ---

mcp = FastMCP(
    service_name="deepsearch",
    description="MCP server for Jina AI's DeepSearch API. DeepSearch combines web searching, reading, and reasoning for comprehensive investigation, providing answers to complex questions requiring iterative reasoning, world-knowledge, or up-to-date information. It is compatible with the OpenAI Chat API schema."
)

# --- API Client Initialization ---

# Initialize the DeepSearch API client
# It reads the API key and base URL from environment variables (JINA_API_KEY, DEEPSEARCH_BASE_URL)
try:
    api_client = DeepSearchClient()
except ValueError as e:
    logger.error(f"Failed to initialize DeepSearchClient: {e}")
    # Optionally, exit or prevent server startup if client initialization fails
    # raise SystemExit(f"Error: {e}") from e
    api_client = None # Set to None to handle gracefully in tool

# --- MCP Tools ---

@mcp.tool(
    name="chat_completion",
    description="Performs a chat completion request using the DeepSearch engine. This involves iterative search, reading, and reasoning to find the best answer to the user's query, especially for complex questions requiring up-to-date information or deep research.",
    input_model=DeepSearchChatParams,
    # Define output model based on whether it's streaming or not - FastMCP might need refinement here
    # For now, let's specify the non-streaming response model and handle streaming via generator
    output_model=DeepSearchChatResponse
)
async def chat_completion(params: DeepSearchChatParams, context: ToolContext) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """
    MCP tool to call the DeepSearch chat completions endpoint.

    Handles both streaming and non-streaming requests based on the `stream` parameter.

    Args:
        params: The validated input parameters matching DeepSearchChatParams.
        context: The MCP ToolContext (unused here but available).

    Returns:
        If stream=False, a dictionary representing the DeepSearchChatResponse.
        If stream=True, an async generator yielding dictionaries representing DeepSearchChatStreamResponse chunks.
        In case of error, a dictionary with an 'error' key.
    """
    if not api_client:
        logger.error("DeepSearchClient is not initialized. Cannot process request.")
        return {"error": "DeepSearch client not available. Check API key configuration."}

    logger.info(f"Received chat_completion request. Streaming: {params.stream}")

    try:
        result = await api_client.chat_completion(params)

        if isinstance(result, AsyncGenerator):
            # Handle streaming response
            logger.info("Streaming response back to MCP client.")
            async def stream_generator():
                try:
                    async for chunk in result:
                        # Yield each chunk as a dictionary
                        yield chunk.model_dump(exclude_none=True)
                except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError, ValidationError) as e:
                    logger.error(f"Error during stream processing in MCP tool: {e}")
                    # Yield an error message if possible, though standard MCP streaming might not support it well
                    yield {"error": f"Stream processing error: {str(e)}"}
                except Exception as e:
                    logger.exception("Unexpected error during stream processing in MCP tool")
                    yield {"error": f"Unexpected stream processing error: {str(e)}"}
            return stream_generator() # Return the async generator
        else:
            # Handle non-streaming response
            logger.info(f"Received non-streaming response (ID: {result.id}). Returning to MCP client.")
            # Return the response as a dictionary
            return result.model_dump(exclude_none=True)

    except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError, ValidationError, json.JSONDecodeError) as e:
        error_message = f"API request failed: {str(e)}"
        if isinstance(e, httpx.HTTPStatusError):
            try:
                # Try to include API error details if available
                error_detail = e.response.json()
                error_message += f" - Detail: {error_detail}"
            except Exception:
                error_message += f" - Body: {e.response.text}"
        logger.error(error_message)
        return {"error": error_message}
    except Exception as e:
        logger.exception("An unexpected error occurred in the chat_completion tool")
        return {"error": f"An unexpected error occurred: {str(e)}"}

# --- Server Shutdown Hook ---

@mcp.app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down MCP server...")
    if api_client:
        await api_client.close()
        logger.info("DeepSearchClient closed.")

# --- Run Server ---

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting DeepSearch MCP server...")
    # Run using Uvicorn. Adjust host, port, and workers as needed.
    uvicorn.run("main:mcp.app", host="0.0.0.0", port=8000, reload=False) # Use reload=True for development
