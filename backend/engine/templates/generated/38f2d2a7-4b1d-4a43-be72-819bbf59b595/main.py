from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
import httpx
import logging
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class DeepsearchQueryParams(BaseModel):
    """Parameters for the Deepsearch API call."""
    query: str = Field(..., description="The search query to send to the Deepsearch API.")
    model: str = Field("deepsearch-default", description="The specific model to use for the search and generation.")
    max_results: int = Field(10, gt=0, le=50, description="Maximum number of search results to consider or return.")
    # Add other potential parameters if the Deepsearch API supports them
    # e.g., search_depth: Optional[str] = Field(None, description="Depth of search (e.g., 'basic', 'advanced')")

class Source(BaseModel):
    """Represents a single source document used for the answer."""
    title: Optional[str] = Field(None, description="Title of the source document.")
    url: Optional[str] = Field(None, description="URL of the source document.")
    snippet: Optional[str] = Field(None, description="Relevant snippet from the source document.")

class DeepsearchUsage(BaseModel):
    """Token usage information from the Deepsearch API."""
    prompt_tokens: Optional[int] = Field(None, description="Tokens used in the prompt.")
    completion_tokens: Optional[int] = Field(None, description="Tokens generated in the completion.")
    total_tokens: Optional[int] = Field(None, description="Total tokens used.")

class DeepsearchResult(BaseModel):
    """Structured result from the Deepsearch API."""
    answer: str = Field(..., description="The generated answer based on the search results.")
    sources: List[Source] = Field([], description="List of sources used to generate the answer.")
    usage: Optional[DeepsearchUsage] = Field(None, description="Token usage information for the API call.")
    # Add other potential fields like query_id, latency, etc.

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Description of the error that occurred.")
    details: Optional[str] = Field(None, description="Additional details about the error.")

# --- API Client ---

class DeepsearchAPIClient:
    """Client to interact with the hypothetical Deepsearch API."""

    DEFAULT_TIMEOUT = 60.0  # seconds

    def __init__(self):
        """Initializes the Deepsearch API client."""
        self.api_key = os.getenv("DEEPSEARCH_API_KEY")
        self.base_url = os.getenv("DEEPSEARCH_API_BASE_URL")

        if not self.api_key:
            logger.error("DEEPSEARCH_API_KEY environment variable not set.")
            raise ValueError("DEEPSEARCH_API_KEY must be set")
        if not self.base_url:
            logger.error("DEEPSEARCH_API_BASE_URL environment variable not set.")
            raise ValueError("DEEPSEARCH_API_BASE_URL must be set")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        # Use a context manager for the client in the actual request method
        # to ensure proper resource cleanup.

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Deepsearch API."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(headers=self.headers, timeout=self.DEFAULT_TIMEOUT) as client:
            try:
                logger.debug(f"Sending {method} request to {url} with payload: {kwargs.get('json')}")
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()  # Raise HTTPStatusError for 4xx/5xx responses
                logger.debug(f"Received successful response ({response.status_code}) from {url}")
                return response.json()
            except httpx.TimeoutException as e:
                logger.error(f"Request timed out after {self.DEFAULT_TIMEOUT}s: {url} - {e}")
                raise TimeoutError(f"Request to Deepsearch API timed out: {e}") from e
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text} for url: {e.request.url}")
                # Attempt to parse error details from response
                try:
                    error_details = e.response.json()
                except Exception:
                    error_details = e.response.text
                raise ConnectionError(f"Deepsearch API request failed with status {e.response.status_code}: {error_details}") from e
            except httpx.RequestError as e:
                logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
                raise ConnectionError(f"Error connecting to Deepsearch API: {e}") from e
            except Exception as e:
                logger.error(f"An unexpected error occurred during the API request: {e}")
                raise

    async def search(self, params: DeepsearchQueryParams) -> Dict[str, Any]:
        """
        Executes a search query using the Deepsearch API.

        Args:
            params: The parameters for the search query.

        Returns:
            The raw dictionary response from the Deepsearch API.

        Raises:
            ValueError: If required parameters are missing.
            TimeoutError: If the request times out.
            ConnectionError: If there's an issue connecting to the API or an HTTP error.
            Exception: For other unexpected errors.
        """
        if not params.query:
            raise ValueError("Query parameter cannot be empty.")

        # Construct the payload based on a hypothetical Deepsearch API structure
        # This might need adjustment based on the actual API specification.
        payload = {
            "model": params.model,
            "query": params.query,
            "max_results": params.max_results,
            # Add other parameters from DeepsearchQueryParams if needed
            # "search_depth": params.search_depth,
        }

        # Assuming the endpoint is something like '/v1/search' or '/search'
        # This should be verified with the actual Deepsearch API documentation.
        endpoint = "/v1/search"

        logger.info(f"Initiating Deepsearch for query: '{params.query[:50]}...' with model: {params.model}")
        response_data = await self._request("POST", endpoint, json=payload)
        logger.info(f"Successfully received Deepsearch response for query: '{params.query[:50]}...'" )
        return response_data

# --- MCP Server ---

mcp = FastMCP(
    name="deepsearch-mcp",
    description="MCP server for interacting with a Deepsearch API.",
    version="1.0.0"
)

# Instantiate the API client (ensure environment variables are set)
try:
    api_client = DeepsearchAPIClient()
except ValueError as e:
    logger.critical(f"Failed to initialize DeepsearchAPIClient: {e}. Ensure .env file is present and variables are set.")
    # Exit or prevent server start if client can't be initialized?
    # For now, we'll let it proceed, but tools will fail.
    api_client = None

@mcp.tool()
async def deep_search(query: str) -> Union[DeepsearchResult, ErrorResponse]:
    """
    Performs a search using the Deepsearch API with default settings.

    Args:
        query: The search query.

    Returns:
        A DeepsearchResult object containing the answer and sources, or an ErrorResponse on failure.
    """
    if not api_client:
        return ErrorResponse(error="API Client not initialized. Check server logs.")

    try:
        params = DeepsearchQueryParams(query=query)
        result_dict = await api_client.search(params)

        # Validate and parse the response using Pydantic models
        # Assuming the API returns keys like 'answer', 'sources', 'usage'
        parsed_result = DeepsearchResult(
            answer=result_dict.get("answer", "No answer provided."),
            sources=[Source(**source) for source in result_dict.get("sources", [])],
            usage=DeepsearchUsage(**result_dict["usage"]) if "usage" in result_dict else None
        )
        return parsed_result
    except (ValueError, TimeoutError, ConnectionError) as e:
        logger.error(f"Error in deep_search for query '{query[:50]}...': {e}")
        return ErrorResponse(error=f"API Request Failed: {type(e).__name__}", details=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in deep_search for query '{query[:50]}...': {e}", exc_info=True)
        return ErrorResponse(error="Internal Server Error", details=str(e))

@mcp.tool()
async def deep_search_custom(params: DeepsearchQueryParams) -> Union[DeepsearchResult, ErrorResponse]:
    """
    Performs a search using the Deepsearch API with custom parameters.

    Args:
        params: A DeepsearchQueryParams object containing the query and custom settings
                (e.g., model, max_results).

    Returns:
        A DeepsearchResult object containing the answer and sources, or an ErrorResponse on failure.
    """
    if not api_client:
        return ErrorResponse(error="API Client not initialized. Check server logs.")

    try:
        logger.info(f"Executing custom deep search with params: {params.dict()}")
        result_dict = await api_client.search(params)

        # Validate and parse the response
        parsed_result = DeepsearchResult(
            answer=result_dict.get("answer", "No answer provided."),
            sources=[Source(**source) for source in result_dict.get("sources", [])],
            usage=DeepsearchUsage(**result_dict["usage"]) if "usage" in result_dict else None
        )
        return parsed_result
    except (ValueError, TimeoutError, ConnectionError) as e:
        logger.error(f"Error in deep_search_custom with params {params.dict()}: {e}")
        return ErrorResponse(error=f"API Request Failed: {type(e).__name__}", details=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in deep_search_custom with params {params.dict()}: {e}", exc_info=True)
        return ErrorResponse(error="Internal Server Error", details=str(e))

# Run the MCP server
if __name__ == "__main__":
    logger.info("Starting Deepsearch MCP server...")
    # Note: Authentication for the MCP server itself (if needed) should be configured
    # via MCP's mechanisms or a reverse proxy, not handled directly here.
    mcp.run()
