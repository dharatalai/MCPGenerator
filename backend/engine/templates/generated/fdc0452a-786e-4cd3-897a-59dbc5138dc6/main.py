import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import (KiteConnectClient, KiteConnectError, InputException,
                    TokenException, PermissionException, NetworkException,
                    GeneralException)
from models import (PlaceOrderParams, ModifyOrderParams, CancelOrderParams,
                    OrderIdResponse)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="Provides tools to manage trading orders (place, modify, cancel) using the Kite Connect API v3."
)

# Initialize API Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit
    # raise ValueError("API Key and Access Token are required.")
    # For now, allow initialization but client calls will fail
    api_client = None
else:
    try:
        api_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
    except Exception as e:
        logger.error(f"Failed to initialize KiteConnectClient: {e}")
        api_client = None

def handle_api_error(tool_name: str, error: Exception) -> Dict[str, Any]:
    """Handles errors from the API client and returns a standardized error response."""
    logger.error(f"Error in tool '{tool_name}': {type(error).__name__} - {error}")
    if isinstance(error, KiteConnectError):
        return {"error": type(error).__name__, "message": str(error), "status_code": getattr(error, 'status_code', None)}
    else:
        return {"error": "InternalServerError", "message": f"An unexpected error occurred: {error}"}

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Places an order of a specified variety.

    Args:
        params: Parameters for placing the order.

    Returns:
        A dictionary containing the order_id upon success, or an error message.
    """
    if not api_client:
        return handle_api_error("place_order", Exception("API Client not initialized. Check environment variables."))

    logger.info(f"Executing place_order with variety: {params.variety}")
    try:
        result: OrderIdResponse = await api_client.place_order(params)
        logger.info(f"Successfully placed order: {result.order_id}")
        return result.dict()
    except Exception as e:
        return handle_api_error("place_order", e)

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modifies attributes of an open or pending order.

    Args:
        params: Parameters for modifying the order.

    Returns:
        A dictionary containing the order_id upon success, or an error message.
    """
    if not api_client:
        return handle_api_error("modify_order", Exception("API Client not initialized. Check environment variables."))

    logger.info(f"Executing modify_order for order_id: {params.order_id}, variety: {params.variety}")
    try:
        result: OrderIdResponse = await api_client.modify_order(params)
        logger.info(f"Successfully modified order: {result.order_id}")
        return result.dict()
    except Exception as e:
        return handle_api_error("modify_order", e)

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancels an open or pending order.

    Args:
        params: Parameters for cancelling the order.

    Returns:
        A dictionary containing the order_id upon success, or an error message.
    """
    if not api_client:
        return handle_api_error("cancel_order", Exception("API Client not initialized. Check environment variables."))

    logger.info(f"Executing cancel_order for order_id: {params.order_id}, variety: {params.variety}")
    try:
        result: OrderIdResponse = await api_client.cancel_order(params)
        logger.info(f"Successfully cancelled order: {result.order_id}")
        return result.dict()
    except Exception as e:
        return handle_api_error("cancel_order", e)

if __name__ == "__main__":
    # Example of how to run the server using uvicorn
    # You would typically run this using: uvicorn main:mcp.app --reload
    import uvicorn
    logger.info("Starting KiteConnectOrders MCP Server")
    if not api_client:
        logger.warning("API Client is not initialized. Tools will return errors. Ensure KITE_API_KEY and KITE_ACCESS_TOKEN are set.")
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
