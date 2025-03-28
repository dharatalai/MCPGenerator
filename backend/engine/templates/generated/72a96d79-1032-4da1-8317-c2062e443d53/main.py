import logging
import os
from typing import List, Optional, Dict, Any, Union, AsyncGenerator

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from models import (
    Message,
    DeepSearchChatInput,
    DeepSearchChatOutput,
    DeepSearchChatChunk,
    # Import other models if needed directly in tool signatures, though using the Input model is cleaner
)
from client import DeepSearchClient, DeepSearchError

# --- Configuration & Initialization ---

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="deepsearch",
    description="MCP server for Jina AI's DeepSearch API. Performs complex search queries with reasoning and web search."
)

# Initialize API Client
# It's good practice to handle potential initialization errors
try:
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        logger.warning("JINA_API_KEY environment variable not set. Client initialization might fail or use defaults.")

    client_timeout_str = os.getenv("MCP_TIMEOUT", "180")
    try:
        client_timeout = float(client_timeout_str)
    except ValueError:
        logger.warning(f"Invalid MCP_TIMEOUT value '{client_timeout_str}'. Using default 180.0 seconds.")
        client_timeout = 180.0

    deepsearch_client = DeepSearchClient(api_key=api_key, timeout=client_timeout)
    logger.info(f"DeepSearchClient initialized for base URL: {deepsearch_client.base_url}")
except ValueError as e:
    logger.exception(f"Failed to initialize DeepSearchClient: {e}")
    # Depending on desired behavior, you might exit or let it fail later
    # For now, we'll let it proceed and fail at request time if key is missing
    deepsearch_client = None # Ensure it's defined, even if None
except Exception as e:
    logger.exception(f"An unexpected error occurred during client initialization: {e}")
    deepsearch_client = None

# --- MCP Tool Definition ---

@mcp.tool(input_model=DeepSearchChatInput)
async def chat_completion(
    messages: List[Message],
    model: str = "jina-deepsearch-v1",
    stream: bool = True,
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = "medium", # type: ignore
    budget_tokens: Optional[int] = None,
    max_attempts: Optional[int] = None,
    no_direct_answer: Optional[bool] = False,
    max_returned_urls: Optional[int] = None,
    structured_output: Optional[Dict[str, Any]] = None,
    good_domains: Optional[List[str]] = None,
    bad_domains: Optional[List[str]] = None,
    only_domains: Optional[List[str]] = None
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """
    Executes a chat completion request using the DeepSearch engine.

    It takes a series of messages, searches the web, reads content, and reasons
    iteratively to generate a comprehensive answer. Supports streaming for
    real-time updates and reasoning steps.

    Args:
        messages: A list of messages comprising the conversation history.
        model: ID of the model to use (default: 'jina-deepsearch-v1').
        stream: Whether to stream back partial progress (default: True).
        reasoning_effort: Constrains reasoning effort ('low', 'medium', 'high').
        budget_tokens: Maximum number of tokens allowed for the process.
        max_attempts: Maximum number of retries for solving the problem.
        no_direct_answer: Forces further thinking/search steps.
        max_returned_urls: Maximum number of URLs in the final answer/chunk.
        structured_output: JSON schema to ensure the final answer matches.
        good_domains: List of domains to prioritize for content retrieval.
        bad_domains: List of domains to strictly exclude from content retrieval.
        only_domains: List of domains to exclusively include in content retrieval.

    Returns:
        If stream=False, a single dictionary representing the chat completion result (DeepSearchChatOutput).
        If stream=True, an async generator yielding dictionaries (DeepSearchChatChunk).

    Raises:
        MCP specific errors on failure.
    """
    if not deepsearch_client:
        logger.error("DeepSearchClient is not initialized. Cannot process request.")
        # FastMCP typically handles exceptions by returning an error response
        raise RuntimeError("DeepSearchClient failed to initialize. Check API key and configuration.")

    try:
        # Create the input object from arguments
        # Pydantic automatically validates types based on annotations
        input_params = DeepSearchChatInput(
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

        logger.info(f"Calling DeepSearch chat_completion tool (stream={stream})")
        result = await deepsearch_client.chat_completion(params=input_params)

        if stream:
            # Return the async generator directly
            async def dict_generator() -> AsyncGenerator[Dict[str, Any], None]:
                async for chunk in result: # type: ignore
                    yield chunk.model_dump(exclude_none=True)
            return dict_generator()
        else:
            # Return the single result as a dictionary
            return result.model_dump(exclude_none=True) # type: ignore

    except DeepSearchError as e:
        logger.error(f"DeepSearch API error in chat_completion tool: {e.message} (Status: {e.status_code})", exc_info=True)
        # Re-raise for FastMCP to handle and return a proper error response
        # You might want to customize the error message or type here
        raise RuntimeError(f"DeepSearch API Error: {e.message}") from e
    except ValidationError as e:
        logger.error(f"Data validation error: {e}", exc_info=True)
        raise ValueError(f"Invalid input or output data: {e}") from e
    except Exception as e:
        logger.exception("An unexpected error occurred in chat_completion tool")
        raise RuntimeError(f"An unexpected server error occurred: {e}") from e

# --- Lifecycle Hooks (Optional) ---

@mcp.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on server shutdown."""
    if deepsearch_client:
        logger.info("Closing DeepSearchClient connection...")
        await deepsearch_client.close()
        logger.info("DeepSearchClient connection closed.")
    else:
        logger.info("No active DeepSearchClient to close.")

# --- Main Execution ---

if __name__ == "__main__":
    # This block allows running the server directly using Uvicorn
    # For production, consider using a process manager like Gunicorn with Uvicorn workers
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    log_level_uvicorn = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"Starting DeepSearch MCP server on {host}:{port}")
    uvicorn.run("main:mcp", host=host, port=port, log_level=log_level_uvicorn, reload=True)
