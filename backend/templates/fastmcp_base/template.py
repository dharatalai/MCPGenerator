"""
Base template for FastMCP servers.
This template provides a starting point for creating MCP servers using FastMCP.
"""
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import json
import httpx
import logging
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP with service name (to be replaced)
mcp = FastMCP("service_name")

# API configuration
BASE_URL = os.getenv("API_BASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")

# Initialize HTTP client
http_client = httpx.AsyncClient(
    base_url=BASE_URL,
    timeout=30.0,
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
)

async def handle_api_response(response: httpx.Response) -> Dict[str, Any]:
    """
    Handle API response and errors.
    
    Args:
        response: The HTTP response from the API
        
    Returns:
        Processed response data
    """
    try:
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_detail = {}
        try:
            error_detail = response.json()
        except:
            error_detail = {"message": response.text}
            
        logger.error(f"API error: {str(e)}, details: {error_detail}")
        return {
            "error": True,
            "status_code": response.status_code,
            "message": str(e),
            "details": error_detail
        }
    except Exception as e:
        logger.error(f"Error processing API response: {str(e)}")
        return {
            "error": True,
            "message": f"Error processing API response: {str(e)}"
        }

@mcp.tool()
async def example_tool(param1: str, param2: Optional[int] = None):
    """
    Example tool that demonstrates how to implement an MCP tool.
    
    Args:
        param1: First parameter description
        param2: Second parameter description (optional)
        
    Returns:
        Result of the API call
    """
    try:
        # Prepare request params
        params = {"param1": param1}
        if param2 is not None:
            params["param2"] = param2
            
        # Make API request
        response = await http_client.get("/example/endpoint", params=params)
        
        # Process response
        result = await handle_api_response(response)
        return result
    except Exception as e:
        logger.error(f"Error in example_tool: {str(e)}")
        return {"error": True, "message": str(e)}

# Clean up when the script exits
import atexit

@atexit.register
def cleanup():
    """Close the HTTP client when the script exits."""
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(http_client.aclose())
        else:
            loop.run_until_complete(http_client.aclose())
    except:
        pass

if __name__ == "__main__":
    mcp.run(transport="stdio") 