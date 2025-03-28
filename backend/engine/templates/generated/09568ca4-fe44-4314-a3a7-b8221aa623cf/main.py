import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from api import DeepSearchClient, DeepSearchAPIError
from models import DeepSearchChatInput, DeepSearchChatResponse

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
    service_name="deepsearch_jina",
    description="MCP service for Jina AI's DeepSearch API. DeepSearch combines web searching, reading, and reasoning to provide comprehensive answers to complex questions, especially those requiring up-to-date information or iterative investigation. It is designed to be compatible with the OpenAI Chat API schema."
)

# Initialize API Client
api_key = os.getenv("JINA_API_KEY")
if not api_key:
    logger.warning("JINA_API_KEY environment variable not set. API calls will likely fail.")
    # Optionally raise an error or exit if the key is absolutely required to start
    # raise ValueError("JINA_API_KEY must be set in the environment.")

api_client = DeepSearchClient(api_key=api_key)

@mcp.tool(input_model=DeepSearchChatInput, returns=DeepSearchChatResponse)
async def chat_completion(params: DeepSearchChatInput) -> Dict[str, Any]:
    """Sends a chat conversation to the DeepSearch model ('jina-deepsearch-v1') for processing.

    The model performs iterative search, reading, and reasoning to generate a
    comprehensive answer, citing sources. Supports text, images (webp, png, jpeg
    encoded as data URIs), and documents (txt, pdf encoded as data URIs) within
    messages. Streaming is recommended and handled by default; this tool returns
    the aggregated final response.

    Args:
        params: Input parameters for the DeepSearch chat completion, conforming to DeepSearchChatInput model.

    Returns:
        The aggregated final response from the DeepSearch model as a dictionary,
        conforming to DeepSearchChatResponse model, or an error dictionary.
    """
    logger.info(f"Received chat_completion request with model: {params.model}")
    try:
        # Ensure streaming is enabled if not explicitly set to false, as recommended
        if params.stream is None:
            params.stream = True
            logger.info("Defaulting to stream=True for chat_completion")
        elif not params.stream:
            logger.warning("Using stream=False. This might lead to timeouts for complex queries.")

        response = await api_client.chat_completion(params)
        logger.info(f"Successfully completed chat_completion request ID: {response.id}")
        # FastMCP expects a dictionary, so convert the Pydantic model
        return response.dict(exclude_none=True)

    except DeepSearchAPIError as e:
        logger.error(f"API error during chat_completion: {e.status_code} - {e.message}")
        return {"error": f"API Error: {e.status_code} - {e.message}"}
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error during chat_completion: {e}")
        return {"error": f"Request timed out: {e}"}
    except httpx.RequestError as e:
        logger.error(f"Request error during chat_completion: {e}")
        return {"error": f"HTTP Request failed: {e}"}
    except Exception as e:
        logger.exception("Unexpected error during chat_completion")
        return {"error": f"An unexpected error occurred: {str(e)}"}

if __name__ == "__main__":
    # Note: Authentication (checking JINA_API_KEY) happens implicitly
    # within the DeepSearchClient initialization and API calls.
    mcp.run()
