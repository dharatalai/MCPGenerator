from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import logging
import asyncio
import os
import json
from dotenv import load_dotenv
import httpx

# Import models and API client
from models import ( 
    DeepSearchChatParams, 
    DeepSearchResponse, 
    Message, 
    Usage, 
    Choice, 
    Delta, 
    Annotation
)
from api import JinaDeepSearchClient

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialize MCP Server ---
mcp = FastMCP(
    service_name="jina_deepsearch",
    description="Provides access to the Jina DeepSearch API for advanced web search and reasoning."
)

# --- Initialize API Client ---
# The client will automatically pick up API key and base URL from environment variables
api_client = JinaDeepSearchClient()

# --- Tool Definition ---
@mcp.tool()
async def chat_completion(params: DeepSearchChatParams) -> Dict[str, Any]:
    """
    Performs a deep search and reasoning process using the Jina DeepSearch API.

    This tool calls the Jina DeepSearch /v1/chat/completions endpoint, which is 
    compatible with the OpenAI Chat API schema. It supports streaming and 
    aggregates the results if streaming is enabled (default).

    Args:
        params: An object containing the parameters for the chat completion, 
                including messages, model, stream preference, and other options.

    Returns:
        A dictionary representing the final aggregated DeepSearchResponse, 
        including the generated content, citations, usage stats, and visited URLs.
        Returns an error dictionary if the API call fails.
    """
    logger.info(f"Received chat_completion request with stream={params.stream}")
    try:
        api_response = await api_client.chat_completion(params)

        if params.stream:
            logger.info("Processing streamed response...")
            final_response = None
            aggregated_content = ""
            aggregated_annotations: List[Annotation] = []
            final_usage: Optional[Usage] = None
            final_visited_urls: Optional[List[str]] = None
            final_read_urls: Optional[List[str]] = None
            final_num_urls: Optional[int] = None
            response_id = None
            created = None
            model = None
            system_fingerprint = None
            finish_reason = None

            async for chunk in api_response: # type: ignore
                # logger.debug(f"Processing chunk: {chunk.model_dump_json(exclude_none=True)}")
                if not final_response: # Initialize with first chunk's metadata
                    final_response = chunk.model_copy(deep=True)
                    response_id = chunk.id
                    created = chunk.created
                    model = chunk.model
                    system_fingerprint = chunk.system_fingerprint
                else: # Update potentially changing metadata like ID for tracking
                    response_id = chunk.id

                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta:
                        if delta.content:
                            aggregated_content += delta.content
                        if delta.annotations:
                            aggregated_annotations.extend(delta.annotations)
                    
                    # Capture finish reason from the last relevant chunk
                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                
                # Capture usage and URL info, usually in the last chunk(s)
                if chunk.usage:
                    final_usage = chunk.usage
                if chunk.visitedURLs:
                    final_visited_urls = chunk.visitedURLs
                if chunk.readURLs:
                    final_read_urls = chunk.readURLs
                if chunk.numURLs:
                    final_num_urls = chunk.numURLs

            if final_response is None:
                 logger.error("Stream ended without receiving any valid chunks.")
                 return {"error": "Stream ended unexpectedly without data."}

            # Construct the final aggregated response object
            aggregated_choice = Choice(
                index=0,
                message=Message(role='assistant', content=aggregated_content),
                delta=None, # Delta is for streaming chunks, message is for final
                logprobs=None,
                finish_reason=finish_reason
            )
            # Add annotations to the final message if needed, or keep them separate?
            # The OpenAI schema puts content in message.content. Let's stick to that.
            # Annotations might need a custom field in the final aggregated response if not part of message.
            # For now, let's create a basic aggregated response structure.

            aggregated_response_data = {
                "id": response_id or "aggregated_stream",
                "object": "chat.completion", # Final object type
                "created": created or 0,
                "model": model or params.model,
                "system_fingerprint": system_fingerprint,
                "choices": [aggregated_choice.model_dump(exclude_none=True)],
                "usage": final_usage.model_dump(exclude_none=True) if final_usage else None,
                "visitedURLs": final_visited_urls,
                "readURLs": final_read_urls,
                "numURLs": final_num_urls,
                # Add aggregated annotations if needed, maybe as a custom field
                "aggregated_annotations": [anno.model_dump(exclude_none=True) for anno in aggregated_annotations] if aggregated_annotations else None
            }
            
            # Validate the constructed response data before returning
            try:
                final_aggregated_response = DeepSearchResponse.model_validate(aggregated_response_data)
                logger.info("Successfully aggregated streamed response.")
                return final_aggregated_response.model_dump(exclude_none=True, by_alias=True)
            except Exception as validation_error:
                logger.error(f"Failed to validate aggregated response: {validation_error}")
                logger.debug(f"Aggregated data causing validation error: {aggregated_response_data}")
                # Return raw aggregated data if validation fails, with an error note
                aggregated_response_data['error'] = f"Failed to validate final aggregated response: {validation_error}"
                return aggregated_response_data

        else: # Non-streaming case
            logger.info("Received non-streamed response.")
            # api_response is already a DeepSearchResponse object
            return api_response.model_dump(exclude_none=True, by_alias=True) # type: ignore

    except httpx.HTTPStatusError as e:
        error_message = f"API Error: {e.response.status_code}"
        try:
            error_details = e.response.json()
            error_message += f" - {error_details}"
        except json.JSONDecodeError:
            error_message += f" - {e.response.text}"
        logger.error(error_message)
        return {"error": error_message, "status_code": e.response.status_code}
    except httpx.RequestError as e:
        error_message = f"Network Error: {e.__class__.__name__} - {str(e)}"
        logger.error(error_message)
        return {"error": error_message}
    except Exception as e:
        error_message = f"An unexpected error occurred: {e.__class__.__name__} - {str(e)}"
        logger.exception(error_message) # Log full traceback for unexpected errors
        return {"error": error_message}

# --- Application Lifecycle Hooks ---
@mcp.app.on_event("shutdown")
async def shutdown_event():
    """Cleanly close the API client connection on server shutdown."""
    logger.info("Shutting down API client...")
    await api_client.close()
    logger.info("API client closed.")

# --- Run Server ---
if __name__ == "__main__":
    # You can run this script directly using `python main.py`
    # or using uvicorn for more production-like features: `uvicorn main:mcp.app --reload`
    logger.info("Starting Jina DeepSearch MCP server...")
    # Note: FastMCP's run() method is simple; for production, use uvicorn directly.
    # mcp.run() # This might block in some environments, use uvicorn recommended
    import uvicorn
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
