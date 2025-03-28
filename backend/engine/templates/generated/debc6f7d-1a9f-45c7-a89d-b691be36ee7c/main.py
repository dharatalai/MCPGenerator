from mcp.server.fastmcp import FastMCP, ToolContext
from typing import Dict, Any, Optional, List, Union, AsyncIterator
import logging
import asyncio
import os
from dotenv import load_dotenv

# Import models and API client
from models import DeepSearchChatInput, DeepSearchChunk, DeepSearchResponse
from api import JinaDeepSearchClient, JinaAPIError, JinaAuthenticationError

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
    description="Provides access to the Jina DeepSearch API, an AI service that performs iterative web searching, reading, and reasoning to answer complex questions. It is fully compatible with the OpenAI Chat API schema."
)

# Initialize API Client
# The client will automatically pick up JINA_API_KEY from the environment
try:
    api_client = JinaDeepSearchClient()
except ValueError as e:
    logger.error(f"Failed to initialize JinaDeepSearchClient: {e}")
    # Decide if the server should exit or continue without a working client
    # For now, let it potentially fail at runtime when the tool is called
    api_client = None 

@mcp.tool()
async def chat_completion(
    params: DeepSearchChatInput,
    context: ToolContext
) -> Union[AsyncIterator[DeepSearchChunk], DeepSearchResponse]:
    """
    Performs deep search and reasoning based on a conversation history using Jina DeepSearch.
    
    It iteratively searches the web, reads content, and reasons to provide a comprehensive 
    answer, citing sources. Suitable for complex questions requiring up-to-date information 
    or multi-hop reasoning. Supports streaming responses for real-time updates.

    Args:
        params: Input parameters including messages, model, streaming options, etc.
        context: The MCP ToolContext.

    Returns:
        If stream=True, returns an async iterator yielding DeepSearchChunk objects.
        The final chunk contains usage statistics and visited URLs.
        If stream=False, returns a single DeepSearchResponse object with the complete 
        answer and metadata (potentially prone to timeouts).
    """
    if not api_client:
         logger.error("Jina API client is not initialized. Check JINA_API_KEY.")
         # You might want to raise a specific MCP error here
         raise RuntimeError("Jina API client failed to initialize.")

    logger.info(f"Executing chat_completion tool for request ID: {context.request_id}")
    try:
        result = await api_client.chat_completion(params)
        # The result is either an AsyncIterator or a DeepSearchResponse object
        # FastMCP handles both correctly.
        return result
    except JinaAuthenticationError as e:
        logger.error(f"Authentication failed for Jina API: {e.error_info}")
        # Re-raise or return a structured error for the MCP client
        # For now, re-raising to let FastMCP handle it as a server error
        raise RuntimeError(f"Jina API Authentication Error: {e.error_info.get('error', 'Invalid API Key')}") from e
    except JinaAPIError as e:
        logger.error(f"Jina API returned an error ({e.status_code}): {e.error_info}")
        raise RuntimeError(f"Jina API Error ({e.status_code}): {e.error_info.get('error', 'API request failed')}") from e
    except TimeoutError as e:
        logger.error(f"Jina API request timed out: {e}")
        raise TimeoutError(f"Jina API request timed out. {e}") from e
    except ConnectionError as e:
        logger.error(f"Could not connect to Jina API: {e}")
        raise ConnectionError(f"Could not connect to Jina API: {e}") from e
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        raise ValueError(f"Data validation error: {e}") from e # e.g., invalid input or response parsing
    except Exception as e:
        logger.exception(f"An unexpected error occurred in chat_completion tool: {e}")
        raise RuntimeError(f"An unexpected server error occurred: {e}") from e

# Example of how to gracefully shutdown the client (optional)
@mcp.on_event("shutdown")
async def shutdown_event():
    if api_client:
        logger.info("Closing Jina API client...")
        await api_client.close()
        logger.info("Jina API client closed.")

if __name__ == "__main__":
    # Run the MCP server using uvicorn (handled by mcp.run())
    # You can configure host, port, etc. via environment variables 
    # or command-line arguments for 'mcp run'
    # Example: MCP_HOST=0.0.0.0 MCP_PORT=8000 mcp run main:mcp
    mcp.run()
