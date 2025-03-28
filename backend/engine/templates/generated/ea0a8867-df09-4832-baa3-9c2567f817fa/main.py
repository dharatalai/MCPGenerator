from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List, Union, AsyncGenerator
import logging
import os
import asyncio
import json
from dotenv import load_dotenv

from models import DeepSearchChatParams, ChatCompletionResponse, ChatCompletionChunk, Message
from client import DeepSearchClient, DeepSearchError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialize MCP Server ---
mcp = FastMCP(
    service_name="deepsearch",
    description="MCP service providing access to the Jina AI DeepSearch API. DeepSearch combines web searching, reading, and reasoning to answer complex questions requiring up-to-date information or iterative investigation."
)

# --- Initialize API Client ---
try:
    api_client = DeepSearchClient()
except ValueError as e:
    logger.error(f"Failed to initialize DeepSearchClient: {e}")
    # Exit if the client cannot be initialized (e.g., missing API key)
    import sys
    sys.exit(f"Error: {e}")

# --- Define MCP Tool ---
@mcp.tool()
async def chat_completion(params: DeepSearchChatParams) -> Dict[str, Any]:
    """
    Performs a deep search and reasoning process using the Jina AI DeepSearch API.

    Accepts chat messages and various parameters to control the search and reasoning.
    Supports both streaming and non-streaming responses.

    Args:
        params (DeepSearchChatParams): Input parameters including messages, model, stream flag, etc.

    Returns:
        Dict[str, Any]:
            - If stream=False, returns the complete Chat Completion object.
            - If stream=True, consumes the stream and returns a consolidated final response
              containing the full message, usage stats, and finish reason.
              (Note: This MCP tool aggregates the stream, it doesn't stream back to the MCP caller).
    """
    logger.info(f"Received chat_completion request (stream={params.stream})")
    try:
        result = await api_client.chat_completion(params)

        if isinstance(result, AsyncGenerator):
            logger.info("Processing stream...")
            # Consume the stream and aggregate the result
            final_response = await _aggregate_stream(result)
            logger.info("Stream processing complete.")
            return final_response
        else:
            # Non-streaming response
            logger.info("Received non-streaming response.")
            # Ensure the response is a dictionary (it should be from the client)
            if isinstance(result, dict):
                return result
            else:
                 logger.error(f"Unexpected non-streaming response type: {type(result)}")
                 return {"error": "Received unexpected response format from API client.", "status_code": 500}

    except DeepSearchError as e:
        logger.error(f"DeepSearch API error in chat_completion tool: {e}")
        return {"error": e.message, "status_code": e.status_code}
    except Exception as e:
        logger.error(f"Unexpected error in chat_completion tool: {e}", exc_info=True)
        return {"error": f"An unexpected internal error occurred: {str(e)}", "status_code": 500}

async def _aggregate_stream(stream: AsyncGenerator[Dict[str, Any], None]) -> Dict[str, Any]:
    """Consumes the SSE stream and aggregates chunks into a final response object."""
    full_content = ""
    final_chunk = None
    all_chunks = [] # Store all chunks for potential debugging or richer info
    final_usage = None
    final_choice = None
    response_id = None
    created_time = None
    model_name = None
    visited_urls = None
    read_urls = None
    num_urls = None

    async for chunk_dict in stream:
        all_chunks.append(chunk_dict)
        try:
            chunk = ChatCompletionChunk.parse_obj(chunk_dict)
            if not response_id: response_id = chunk.id
            if not created_time: created_time = chunk.created
            if not model_name: model_name = chunk.model

            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_content += delta.content
                if chunk.choices[0].finish_reason:
                    final_choice = chunk.choices[0] # Store the choice with the finish reason

            # Usage info usually comes in the last chunk
            if chunk.usage:
                final_usage = chunk.usage

            # DeepSearch specific fields might appear in later chunks
            if chunk.visitedURLs is not None: visited_urls = chunk.visitedURLs
            if chunk.readURLs is not None: read_urls = chunk.readURLs
            if chunk.numURLs is not None: num_urls = chunk.numURLs

            final_chunk = chunk # Keep track of the last chunk

        except Exception as e:
            logger.warning(f"Failed to process or validate stream chunk: {e}. Chunk: {chunk_dict}")
            # Continue processing other chunks if possible

    # Construct the final response mimicking ChatCompletionResponse structure
    if not final_choice:
        # If stream ended unexpectedly without a finish_reason
        logger.warning("Stream ended without a final choice containing finish_reason.")
        if final_chunk and final_chunk.choices: # Use last known choice
             final_choice = final_chunk.choices[0]
        else: # Create a placeholder choice if none exists
             final_choice = Choice(index=0, message=Message(role="assistant", content=full_content), finish_reason="incomplete")
    else:
         # Ensure the final choice has the full aggregated content
         final_choice.message = Message(role="assistant", content=full_content)
         final_choice.delta = None # Remove delta from final aggregated choice

    aggregated_response = {
        "id": response_id or "unknown_stream_id",
        "object": "chat.completion", # Mimic non-streaming object type
        "created": created_time or 0,
        "model": model_name or "unknown_model",
        "choices": [final_choice.dict(exclude_none=True)] if final_choice else [],
        "usage": final_usage.dict(exclude_none=True) if final_usage else None,
        "visitedURLs": visited_urls,
        "readURLs": read_urls,
        "numURLs": num_urls,
        "_raw_chunks_count": len(all_chunks) # Add metadata about the stream aggregation
    }

    return aggregated_response

# --- Graceful Shutdown --- 
@mcp.app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down MCP server...")
    await api_client.close()
    logger.info("DeepSearch client closed.")

# --- Run Server ---
if __name__ == "__main__":
    # Use uvicorn to run the server
    # Example: uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
    logger.info("Starting DeepSearch MCP server. Run with Uvicorn, e.g.:")
    logger.info("uvicorn main:mcp.app --host 0.0.0.0 --port 8000")
    # The following line is for simple execution context, but uvicorn is preferred for production
    # mcp.run() # This might not work as expected for async shutdown, use uvicorn
