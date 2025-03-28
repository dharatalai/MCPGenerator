from mcp.server.fastmcp import FastMCP, ToolContext
from typing import AsyncIterator, Union, List, Optional, Dict, Any
import logging
import os
import asyncio
from dotenv import load_dotenv
import httpx

# Import models and API client
from models import DeepSearchInput, DeepSearchResponse, DeepSearchChunk, Message
from api import JinaDeepSearchClient

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
    description="Integrates with Jina AI's DeepSearch API for advanced web search and reasoning."
)

# --- API Client Initialization ---

# Initialize the Jina DeepSearch client
# It will automatically pick up the API key from the JINA_API_KEY environment variable
try:
    api_client = JinaDeepSearchClient()
except ValueError as e:
    logger.error(f"Failed to initialize JinaDeepSearchClient: {e}")
    # Depending on deployment strategy, you might want to exit or handle this differently
    api_client = None # Set to None to prevent tool usage if initialization fails

# --- Tool Definition ---

@mcp.tool()
async def chat_completion(
    ctx: ToolContext,
    messages: List[Message],
    model: str = "jina-deepsearch-v1",
    stream: bool = True,
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = "medium",
    budget_tokens: Optional[int] = None,
    max_attempts: Optional[int] = None,
    no_direct_answer: bool = False,
    max_returned_urls: Optional[int] = None,
    structured_output: Optional[Dict[str, Any]] = None,
    good_domains: Optional[List[str]] = None,
    bad_domains: Optional[List[str]] = None,
    only_domains: Optional[List[str]] = None
) -> Union[DeepSearchResponse, AsyncIterator[DeepSearchChunk]]:
    """
    Performs a deep search and reasoning process based on the provided conversation history and query.

    This tool iteratively searches the web, reads relevant content, and reasons to formulate the best possible answer.
    Suitable for complex questions requiring up-to-date information or multi-hop reasoning.
    Supports streaming responses.

    Args:
        ctx: The MCP ToolContext.
        messages: A list of messages comprising the conversation history.
        model: ID of the model to use (default: 'jina-deepsearch-v1').
        stream: Whether to stream back partial progress (default: True).
        reasoning_effort: Reasoning effort level ('low', 'medium', 'high', default: 'medium').
        budget_tokens: Maximum tokens allowed for the process.
        max_attempts: Maximum retry attempts for solving.
        no_direct_answer: Force search/thinking steps (default: False).
        max_returned_urls: Maximum URLs in the final answer.
        structured_output: JSON schema for structured output.
        good_domains: Prioritized domains.
        bad_domains: Excluded domains.
        only_domains: Exclusively included domains.

    Returns:
        If stream=False, a DeepSearchResponse object.
        If stream=True, an async iterator yielding DeepSearchChunk objects.

    Raises:
        ConnectionError: If the API client cannot connect.
        TimeoutError: If the API request times out.
        Exception: For other API or processing errors.
    """
    if not api_client:
        logger.error("JinaDeepSearchClient is not initialized. Cannot perform chat completion.")
        # You might want to return a specific error structure or raise an exception
        # depending on how the calling agent should handle this.
        raise RuntimeError("Jina DeepSearch API client is not configured.")

    # Construct the input object
    input_data = DeepSearchInput(
        messages=messages,
        model=model,
        stream=stream,
        reasoning_effort=reasoning_effort,
        budget_tokens=budget_tokens,
        max_attempts=max_attempts,
        no_direct_answer=no_direct_answer,
        max_returned_urls=max_returned_urls,
        structured_output=structured_output,
        good_domains=good_domains,
        bad_domains=bad_domains,
        only_domains=only_domains
    )

    logger.info(f"Calling Jina DeepSearch API (stream={stream}) with model '{model}'.")

    try:
        result = await api_client.chat_completion(params=input_data)

        if stream:
            # If streaming, return the async iterator directly
            logger.info("Streaming response started.")
            # The iterator needs to be consumed by the caller
            async def stream_wrapper():
                try:
                    async for chunk in result:
                        yield chunk
                    logger.info("Streaming response finished.")
                except Exception as e:
                    logger.error(f"Error during stream consumption: {e}", exc_info=True)
                    # Re-raise or handle as appropriate for the MCP framework
                    raise
            return stream_wrapper()
        else:
            # If not streaming, return the complete response object
            logger.info(f"Received non-streaming response. Usage: {result.usage}")
            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"API request failed with status {e.response.status_code}: {e.response.text}")
        # Re-raise or convert to a more user-friendly error
        raise Exception(f"Jina API Error {e.response.status_code}: {e.response.text}") from e
    except (ConnectionError, TimeoutError, httpx.RequestError) as e:
        logger.error(f"API connection/timeout error: {e}")
        raise ConnectionError(f"Failed to connect to Jina DeepSearch API: {e}") from e
    except Exception as e:
        logger.exception(f"An unexpected error occurred in chat_completion tool: {e}")
        raise Exception(f"An internal error occurred: {e}") from e

# --- Server Shutdown Hook ---

@mcp.on_event("shutdown")
async def shutdown_event():
    """Gracefully close the API client on server shutdown."""
    if api_client:
        logger.info("Closing Jina DeepSearch API client...")
        await api_client.close()
        logger.info("Jina DeepSearch API client closed.")
    else:
        logger.info("No API client to close.")

# --- Run Server ---

if __name__ == "__main__":
    logger.info("Starting Jina DeepSearch MCP server...")
    mcp.run()
