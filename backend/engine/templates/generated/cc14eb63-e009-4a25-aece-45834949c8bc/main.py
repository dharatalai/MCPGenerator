from mcp.server.fastmcp import FastMCP, ToolContext
from typing import Dict, Any, Optional, List, Union, AsyncIterator
import logging
import os
from dotenv import load_dotenv
import asyncio

# Import models and API client
from models import (
    DeepSearchChatInput, 
    DeepSearchChatResponse, 
    DeepSearchChatResponseChunk,
    Message # Import Message if needed directly in tool signature, though using Input model is better
)
from api import JinaDeepSearchClient

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
    description="MCP server for Jina AI DeepSearch, providing advanced search, reading, and reasoning capabilities."
)

# Initialize API Client
# Consider adding error handling for missing API key during initialization if strict
jina_client = JinaDeepSearchClient()

@mcp.tool()
async def chat_completion(
    ctx: ToolContext,
    messages: List[Dict[str, Any]] = [], # Use Dict temporarily, convert to Message inside
    model: str = "jina-deepsearch-v1",
    stream: bool = True,
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = "medium", # type: ignore
    budget_tokens: Optional[int] = None,
    max_attempts: Optional[int] = None,
    no_direct_answer: bool = False,
    max_returned_urls: Optional[int] = None,
    structured_output: Optional[Dict[str, Any]] = None,
    good_domains: Optional[List[str]] = None,
    bad_domains: Optional[List[str]] = None,
    only_domains: Optional[List[str]] = None
) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
    """
    Performs a deep search and reasoning process based on a conversation history.

    This tool simulates an agent that searches the web, reads relevant content, 
    and iteratively refines its understanding to answer complex questions.

    Args:
        ctx: The MCP ToolContext.
        messages: A list of messages comprising the conversation history.
                  Each message should be a dict with 'role' and 'content'.
                  Content can be str or list of content parts (text, image_url, file_url).
        model: ID of the model to use (default: 'jina-deepsearch-v1').
        stream: Whether to stream back partial progress (default: True).
        reasoning_effort: Constraint on reasoning effort ('low', 'medium', 'high', default: 'medium').
        budget_tokens: Maximum number of tokens allowed.
        max_attempts: Maximum number of retries.
        no_direct_answer: Force search/thinking steps (default: False).
        max_returned_urls: Maximum number of URLs in the final answer.
        structured_output: JSON schema for the final answer structure.
        good_domains: List of domains to prioritize.
        bad_domains: List of domains to strictly exclude.
        only_domains: List of domains to exclusively include.

    Returns:
        If stream=False, a dictionary representing DeepSearchChatResponse.
        If stream=True, an async iterator yielding dictionaries representing DeepSearchChatResponseChunk.
    """
    logger.info(f"Received chat_completion request. Stream: {stream}")
    try:
        # --- Input Validation and Preparation ---
        # Pydantic expects List[Message], so we convert the input dict list
        # This provides validation for the message structure
        validated_messages = [Message.model_validate(msg) for msg in messages]

        input_data = DeepSearchChatInput(
            messages=validated_messages,
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

        # --- API Call --- 
        result = await jina_client.chat_completion(input_data)

        # --- Response Handling --- 
        if isinstance(result, AsyncIterator):
            # Streaming response
            logger.info("Returning streaming response iterator.")
            async def stream_wrapper():
                try:
                    async for chunk in result:
                        yield chunk.model_dump(exclude_none=True)
                except Exception as e:
                    logger.error(f"Error during stream processing: {e}", exc_info=True)
                    # Depending on desired behavior, you might yield an error chunk
                    # or just stop the stream.
                    yield {"error": f"Stream processing error: {str(e)}"}
            return stream_wrapper()
        else:
            # Non-streaming response
            logger.info(f"Returning non-streaming response. ID: {result.id}")
            return result.model_dump(exclude_none=True)

    except Exception as e:
        logger.error(f"Error in chat_completion tool: {e}", exc_info=True)
        # Return a structured error that MCP can handle
        # TODO: Define a standard error structure if needed
        return {"error": str(e), "details": "Failed to process Jina DeepSearch request."} 

async def shutdown():
    """Gracefully shutdown the API client."""
    logger.info("Shutting down Jina DeepSearch client...")
    await jina_client.close()
    logger.info("Jina DeepSearch client shut down.")

mcp.add_event_handler("shutdown", shutdown)

if __name__ == "__main__":
    # Note: FastMCP's run() method handles the ASGI server setup.
    # You might configure host, port, etc., via environment variables
    # or directly in the run() call if needed.
    logger.info("Starting Jina DeepSearch MCP server...")
    mcp.run()
