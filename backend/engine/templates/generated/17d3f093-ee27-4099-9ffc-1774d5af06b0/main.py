import logging
import os
import asyncio
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from api import DeepSearchAPIClient, DeepSearchAPIError
from models import ChatCompletionParams, ChatCompletionResponse

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
    service_name="deepsearch",
    description="MCP service for Jina AI's DeepSearch API, combining web searching, reading, and reasoning."
)

# Initialize API Client
try:
    api_client = DeepSearchAPIClient()
except ValueError as e:
    logger.error(f"Failed to initialize API client: {e}")
    # Optionally exit or prevent server start if API key is essential
    # exit(1)
    api_client = None # Allow server to start but tools will fail

@mcp.tool()
async def chat_completion(params: ChatCompletionParams) -> Dict[str, Any]:
    """
    Perform a deep search and reasoning process to answer a query using Jina AI's DeepSearch API.

    This tool mimics OpenAI's Chat Completion but enhances it with iterative web search,
    reading, and reasoning capabilities.

    Args:
        params: Parameters for the chat completion request, including messages, model, and optional settings.

    Returns:
        A dictionary containing the aggregated response from the DeepSearch process,
        including the answer, usage statistics, and potentially cited URLs within the content.
        Returns an error dictionary if the API call fails.
    """
    if not api_client:
        logger.error("DeepSearch API client is not initialized. Check JINA_API_KEY.")
        return {"error": "API client not initialized. Missing JINA_API_KEY?"}

    logger.info(f"Received chat_completion request with model: {params.model}")

    try:
        # Ensure streaming is enabled for aggregation, as recommended
        # The API client handles the aggregation internally.
        if not params.stream:
             logger.warning("Streaming is disabled. This might lead to timeouts for complex queries. Enabling stream=True is recommended.")
             # Force stream=True internally for aggregation, or handle non-streaming if necessary
             # For simplicity, we rely on the client handling the specified stream param.

        response_data = await api_client.chat_completion(params)

        # Validate and structure the response using Pydantic model
        # The client already returns a dict, potentially matching ChatCompletionResponse
        # We can parse it here for validation, though the client might do it too.
        try:
            # Assuming response_data is a dict matching ChatCompletionResponse structure
            structured_response = ChatCompletionResponse.model_validate(response_data)
            logger.info(f"Successfully completed chat_completion request ID: {structured_response.id}")
            return structured_response.model_dump(exclude_none=True)
        except Exception as pydantic_error:
            logger.error(f"Failed to parse API response: {pydantic_error}. Raw data: {response_data}")
            # Return raw data if parsing fails but request was successful
            return response_data

    except DeepSearchAPIError as e:
        logger.error(f"API Error during chat_completion: {e.status_code} - {e.message}")
        return {"error": f"API Error: {e.status_code} - {e.message}"}
    except asyncio.TimeoutError:
        logger.error("Request timed out during chat_completion.")
        return {"error": "Request timed out."}
    except Exception as e:
        logger.exception(f"Unexpected error during chat_completion: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

if __name__ == "__main__":
    if not api_client:
        print("ERROR: DeepSearch API client failed to initialize.")
        print("Please ensure the JINA_API_KEY environment variable is set correctly in your .env file or environment.")
    else:
        print("Starting DeepSearch MCP server...")
        mcp.run()
