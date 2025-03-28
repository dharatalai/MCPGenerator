from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import logging
import asyncio
import os
from dotenv import load_dotenv

from models import DeepSearchChatInput, DeepSearchChatOutput, Message, TextContent
from api import DeepSearchAPIClient, DeepSearchAPIError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="deepsearch",
    description="MCP server for Jina AI's DeepSearch API. Provides advanced search capabilities combining web search, content reading, and reasoning."
)

# Initialize API Client
# The client will automatically pick up JINA_API_KEY from the environment
try:
    api_client = DeepSearchAPIClient()
    logger.info("DeepSearch API Client initialized successfully.")
except ValueError as e:
    logger.error(f"Failed to initialize DeepSearch API Client: {e}")
    # Optionally, exit or prevent server start if API key is essential
    # raise SystemExit(f"Error: {e}")
    api_client = None # Set to None to handle gracefully in tool calls

@mcp.tool()
async def chat_completion(params: DeepSearchChatInput) -> Dict[str, Any]:
    """
    Initiates a DeepSearch process based on a conversation history.

    Args:
        params (DeepSearchChatInput): Input parameters containing the list of messages and optional settings.

    Returns:
        Dict[str, Any]: A dictionary containing the search results (answer, sources, usage) 
                      or an error message.
    """
    if not api_client:
        logger.error("DeepSearch API Client is not initialized. Cannot process request.")
        return {"error": "DeepSearch API Client not initialized. Check API key configuration."}

    logger.info(f"Received chat_completion request with {len(params.messages)} messages.")
    
    # Basic validation: Ensure there's at least one message
    if not params.messages:
        logger.warning("Received chat_completion request with no messages.")
        return {"error": "Input must contain at least one message."}

    try:
        # Ensure content is correctly formatted before sending to API client
        # (Pydantic validation handles basic structure, but complex content needs checking)
        # The API client now handles the detailed serialization
        pass 
            
        result: DeepSearchChatOutput = await api_client.chat_completion(params)
        logger.info(f"Successfully completed DeepSearch request. Answer length: {len(result.answer)}")
        # Return the Pydantic model converted to a dictionary
        return result.dict(exclude_none=True) 

    except DeepSearchAPIError as e:
        logger.error(f"DeepSearch API error: Status={e.status_code}, Info={e.error_info}")
        return {"error": f"DeepSearch API Error: {e.status_code} - {e.error_info}"}
    except httpx.TimeoutException:
        logger.error("DeepSearch API request timed out.")
        return {"error": "Request to DeepSearch API timed out."}
    except httpx.RequestError as e:
        logger.error(f"Network error connecting to DeepSearch API: {e}")
        return {"error": f"Network error communicating with DeepSearch API: {e}"}
    except ValueError as e:
        # Handle parsing errors from API response or validation errors
        logger.error(f"Data validation or parsing error: {e}")
        return {"error": f"Data validation or parsing error: {e}"}
    except Exception as e:
        logger.exception("An unexpected error occurred in chat_completion tool.") # Use exception to log stack trace
        return {"error": f"An unexpected internal error occurred: {str(e)}"}

# Graceful shutdown
@mcp.app.on_event("shutdown")
async def shutdown_event():
    if api_client:
        logger.info("Closing DeepSearch API client...")
        await api_client.close()
        logger.info("DeepSearch API client closed.")

if __name__ == "__main__":
    # MCP's run() method starts the Uvicorn server
    # Configuration can be done via environment variables like MCP_PORT, MCP_HOST
    logger.info("Starting DeepSearch MCP server...")
    mcp.run()
