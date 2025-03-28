from mcp.server.fastmcp import FastMCP, StreamingToolResponse
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
import logging
import os
from dotenv import load_dotenv

# Import models and client
from models import (
    DeepSearchChatInput,
    DeepSearchChatCompletion,
    DeepSearchChatCompletionChunk
)
from client import (
    DeepSearchClient,
    DeepSearchError,
    AuthenticationError,
    RateLimitError,
    BadRequestError,
    TimeoutError,
    InternalServerError,
    NetworkError
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="deepsearch",
    description="MCP service for Jina AI's DeepSearch API. Provides advanced search capabilities by combining web searching, reading, and reasoning to answer complex questions. It is designed to be compatible with the OpenAI Chat API schema."
)

# Initialize DeepSearch API Client
try:
    deepsearch_client = DeepSearchClient()
except ValueError as e:
    logger.error(f"Failed to initialize DeepSearchClient: {e}")
    # Optionally exit or prevent server start if client init fails
    # exit(1)
    deepsearch_client = None # Allow server to start but tools will fail

@mcp.tool()
async def chat_completion(params: DeepSearchChatInput) -> Union[DeepSearchChatCompletion, StreamingToolResponse]:
    """
    Performs a deep search and reasoning process based on a series of messages.
    It iteratively searches the web, reads content, and reasons to find the best answer
    to the user's query. Supports streaming responses.

    Args:
        params: Input parameters matching the DeepSearchChatInput model.

    Returns:
        If stream=True, a StreamingToolResponse yielding DeepSearchChatCompletionChunk objects.
        If stream=False, a DeepSearchChatCompletion object.

    Raises:
        MCP specific errors mapping from client exceptions.
    """
    if not deepsearch_client:
        logger.error("DeepSearchClient is not initialized. Check API key configuration.")
        # You might want to raise a specific MCP error here
        # For now, returning an error dictionary
        return {"error": "DeepSearch client not initialized. Check JINA_API_KEY."} # Or raise an appropriate MCP exception

    try:
        logger.info(f"Received chat_completion request. Streaming: {params.stream}")
        result = await deepsearch_client.chat_completion(params)

        if params.stream:
            if isinstance(result, AsyncGenerator):
                logger.info("Returning streaming response.")
                # Wrap the async generator in StreamingToolResponse
                async def generator_wrapper():
                    try:
                        async for chunk in result:
                            yield chunk.dict() # Yield dictionary representation for MCP
                    except DeepSearchError as e:
                        logger.error(f"Error during stream processing: {e}")
                        # Yield an error chunk or handle differently
                        yield {"error": str(e), "type": type(e).__name__}
                    except Exception as e:
                        logger.error(f"Unexpected error during stream processing: {e}", exc_info=True)
                        yield {"error": f"Unexpected stream error: {str(e)}", "type": "UnexpectedStreamError"}

                return StreamingToolResponse(content=generator_wrapper())
            else:
                # This case should ideally not happen if the client logic is correct
                logger.error("Expected an async generator for streaming, but got a different type.")
                return {"error": "Internal server error: Unexpected response type for streaming."} # Or raise
        else:
            if isinstance(result, DeepSearchChatCompletion):
                logger.info("Returning non-streaming response.")
                return result.dict() # Return dictionary representation for MCP
            else:
                # This case should ideally not happen
                logger.error("Expected a DeepSearchChatCompletion object for non-streaming, but got a different type.")
                return {"error": "Internal server error: Unexpected response type for non-streaming."} # Or raise

    # Map specific client errors to potential MCP error responses or logged events
    except AuthenticationError as e:
        logger.error(f"Authentication Error: {e}")
        return {"error": str(e), "type": "AuthenticationError"}
    except RateLimitError as e:
        logger.error(f"Rate Limit Error: {e}")
        return {"error": str(e), "type": "RateLimitError"}
    except BadRequestError as e:
        logger.error(f"Bad Request Error: {e}")
        return {"error": str(e), "type": "BadRequestError"}
    except TimeoutError as e:
        logger.error(f"Timeout Error: {e}")
        return {"error": str(e), "type": "TimeoutError"}
    except InternalServerError as e:
        logger.error(f"Internal Server Error: {e}")
        return {"error": str(e), "type": "InternalServerError"}
    except NetworkError as e:
        logger.error(f"Network Error: {e}")
        return {"error": str(e), "type": "NetworkError"}
    except DeepSearchError as e:
        logger.error(f"DeepSearch API Error: {e}")
        return {"error": str(e), "type": "DeepSearchError"}
    except Exception as e:
        logger.exception("An unexpected error occurred in the chat_completion tool.") # Log full traceback
        return {"error": f"An unexpected internal error occurred: {str(e)}", "type": "UnexpectedError"}

# Run the MCP server
if __name__ == "__main__":
    # You can configure host and port here or via environment variables
    # Uvicorn is typically used for production runs, e.g.:
    # uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
    logger.info("Starting MCP server for DeepSearch...")
    # FastMCP's run() is simple, for more control use uvicorn directly
    # mcp.run() # This might block in ways not ideal for async; direct uvicorn is better

    # To run programmatically (though CLI is standard):
    import uvicorn
    uvicorn.run(mcp.app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
