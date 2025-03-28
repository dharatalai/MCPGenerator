from mcp.server.fastmcp import FastMCP, ToolContext
from typing import Dict, Any, AsyncGenerator, Union
import logging
import os
from dotenv import load_dotenv

# Import local modules
from .models import DeepSearchChatInput, DeepSearchChatOutput, Message # Ensure models are imported
from .client import DeepSearchClient, DeepSearchError, AuthenticationError, RateLimitError, BadRequestError, APIError, TimeoutError, ConnectionError

# --- Initialization --- #

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="deepsearch",
    description="MCP server for Jina AI's DeepSearch API, providing advanced search, reading, and reasoning capabilities."
)

# Initialize API Client
# Consider adding error handling for client initialization if API key is missing
try:
    api_client = DeepSearchClient()
except ValueError as e:
    logger.error(f"Failed to initialize DeepSearchClient: {e}")
    # Decide how to handle this - exit or run without a functional client?
    # For now, we'll let it proceed but tools will fail.
    api_client = None

# --- MCP Tools --- #

@mcp.tool()
async def chat_completion(params: DeepSearchChatInput, context: ToolContext) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """
    Performs iterative search, reading, and reasoning using the DeepSearch model.

    Takes a conversation history and various parameters to control the search and reasoning process.
    Returns a detailed response including the answer, citations, and usage statistics.
    Supports both streaming (default) and non-streaming responses.

    Args:
        params (DeepSearchChatInput): Input parameters including messages, model, stream, etc.
        context (ToolContext): The MCP tool context.

    Returns:
        Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        - If stream=False, returns a dictionary conforming to DeepSearchChatOutput.
        - If stream=True, returns an async generator yielding dictionary chunks.

    Raises:
        Will convert specific client errors into MCP-compatible error responses.
    """
    if not api_client:
        logger.error("DeepSearchClient is not initialized. Cannot perform chat completion.")
        # You might want to return a more structured error compatible with MCP/OpenAI schema
        return {"error": "DeepSearch client not initialized. Check API key configuration."}

    logger.info(f"Received chat_completion request for model {params.model}. Stream={params.stream}")

    try:
        result = await api_client.chat_completion(params)

        if params.stream:
            # If streaming, return the async generator directly
            logger.info("Streaming response started.")
            # The generator needs to be consumed by the caller (FastMCP handles this)
            async def stream_wrapper():
                try:
                    async for chunk in result:
                        yield chunk
                    logger.info("Streaming response completed.")
                except DeepSearchError as e:
                     logger.error(f"Error during stream consumption: {type(e).__name__} - {e}")
                     # Yield an error chunk if possible, or handle appropriately
                     # This part might be tricky depending on FastMCP's stream error handling
                     yield {"error": f"{type(e).__name__}: {str(e)}", "status_code": getattr(e, 'status_code', None)}
                except Exception as e:
                    logger.error(f"Unexpected error during stream consumption: {e}")
                    yield {"error": f"Unexpected stream error: {str(e)}"}

            return stream_wrapper()
        else:
            # If not streaming, return the complete result dictionary
            logger.info("Non-streaming response received.")
            # Optionally validate/parse with DeepSearchChatOutput here if needed
            # parsed_output = DeepSearchChatOutput(**result)
            # return parsed_output.model_dump()
            return result

    except AuthenticationError as e:
        logger.error(f"Authentication Error: {e}")
        # Return an error structure compatible with OpenAI API errors if possible
        return {"error": {"message": str(e), "type": "authentication_error", "code": e.status_code}}
    except RateLimitError as e:
        logger.error(f"Rate Limit Error: {e}")
        return {"error": {"message": str(e), "type": "rate_limit_error", "code": e.status_code}}
    except BadRequestError as e:
        logger.error(f"Bad Request Error: {e}")
        return {"error": {"message": str(e), "type": "invalid_request_error", "code": e.status_code}}
    except TimeoutError as e:
        logger.error(f"Timeout Error: {e}")
        return {"error": {"message": str(e), "type": "timeout_error", "code": 504}} # Use 504 for timeout
    except APIError as e:
        logger.error(f"API Error: {e}")
        return {"error": {"message": str(e), "type": "api_error", "code": e.status_code}}
    except ConnectionError as e:
        logger.error(f"Connection Error: {e}")
        return {"error": {"message": str(e), "type": "connection_error", "code": 503}} # Use 503 for connection issues
    except DeepSearchError as e:
        logger.error(f"DeepSearch Error: {e}")
        return {"error": {"message": str(e), "type": "deepsearch_error", "code": getattr(e, 'status_code', 500)}}
    except Exception as e:
        logger.exception("An unexpected error occurred in chat_completion tool.") # Log full traceback
        return {"error": {"message": f"An unexpected server error occurred: {str(e)}", "type": "internal_server_error", "code": 500}}

# --- Lifecycle Hooks --- #

@mcp.on_event("shutdown")
async def shutdown_event():
    """Cleanly close the API client on server shutdown."""
    if api_client:
        await api_client.close()
    logger.info("DeepSearch MCP server shutting down.")

# --- Run Server --- #

if __name__ == "__main__":
    # Note: To run with Uvicorn for production:
    # uvicorn main:mcp.app --host 0.0.0.0 --port 8000
    # FastMCP's run() is mainly for development/simplicity
    logger.info("Starting DeepSearch MCP server...")
    mcp.run()
