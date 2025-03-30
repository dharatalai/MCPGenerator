from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import logging
import os
from dotenv import load_dotenv

from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams, OrderResponse
from client import KiteConnectClient, KiteApiException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="kite_connect_orders",
    description="Provides tools to interact with the Kite Connect Orders API, allowing users to place, modify, cancel, and retrieve order and trade information."
)

# Initialize Kite Connect Client
# Ensure KITE_API_KEY and KITE_ACCESS_TOKEN are set in your environment or .env file
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    # Optionally raise an exception or exit if credentials are required at startup
    # raise ValueError("API Key and Access Token not configured")
    # For now, we allow it to proceed, but client calls will fail.
    kite_client = None
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token)
    except Exception as e:
        logger.exception("Failed to initialize KiteConnectClient")
        kite_client = None

def handle_api_error(tool_name: str, error: Exception) -> Dict[str, Any]:
    """Centralized error handler for API calls."""
    logger.error(f"Error in {tool_name}: {error}", exc_info=True)
    if isinstance(error, KiteApiException):
        return {"error": error.message, "code": error.code, "status": "error"}
    else:
        # General exception
        return {"error": f"An unexpected error occurred: {str(error)}", "status": "error"}

@mcp.tool()
def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Places an order of a specific variety (regular, amo, co, iceberg, auction).

    Args:
        params: Order placement parameters including variety, tradingsymbol, exchange, etc.

    Returns:
        A dictionary containing the 'order_id' of the placed order or an error message.
    """
    if not kite_client:
        return {"error": "Kite Connect client not initialized. Check API Key/Access Token.", "status": "error"}

    logger.info(f"Placing order with params: {params.dict(exclude_none=True)}")
    try:
        response_data = await kite_client.place_order(params)
        logger.info(f"Order placed successfully: {response_data}")
        # Ensure the response matches the expected structure
        if isinstance(response_data, dict) and "order_id" in response_data:
             return OrderResponse(order_id=response_data["order_id"]).dict()
        else:
             logger.error(f"Unexpected response format from place_order: {response_data}")
             return {"error": "Unexpected response format from API", "details": response_data, "status": "error"}

    except Exception as e:
        return handle_api_error("place_order", e)

@mcp.tool()
def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modifies attributes of a pending regular or CO order.

    Args:
        params: Order modification parameters including variety, order_id, and fields to modify.

    Returns:
        A dictionary containing the 'order_id' of the modified order or an error message.
    """
    if not kite_client:
        return {"error": "Kite Connect client not initialized. Check API Key/Access Token.", "status": "error"}

    logger.info(f"Modifying order with params: {params.dict(exclude_none=True)}")
    try:
        response_data = await kite_client.modify_order(params)
        logger.info(f"Order modified successfully: {response_data}")
        # Ensure the response matches the expected structure
        if isinstance(response_data, dict) and "order_id" in response_data:
            return OrderResponse(order_id=response_data["order_id"]).dict()
        else:
            logger.error(f"Unexpected response format from modify_order: {response_data}")
            return {"error": "Unexpected response format from API", "details": response_data, "status": "error"}

    except Exception as e:
        return handle_api_error("modify_order", e)

@mcp.tool()
def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """
    Cancels a pending order.

    Args:
        params: Order cancellation parameters including variety and order_id.

    Returns:
        A dictionary containing the 'order_id' of the cancelled order or an error message.
    """
    if not kite_client:
        return {"error": "Kite Connect client not initialized. Check API Key/Access Token.", "status": "error"}

    logger.info(f"Cancelling order with params: {params.dict()}")
    try:
        response_data = await kite_client.cancel_order(params)
        logger.info(f"Order cancelled successfully: {response_data}")
        # Ensure the response matches the expected structure
        if isinstance(response_data, dict) and "order_id" in response_data:
            return OrderResponse(order_id=response_data["order_id"]).dict()
        else:
            logger.error(f"Unexpected response format from cancel_order: {response_data}")
            return {"error": "Unexpected response format from API", "details": response_data, "status": "error"}

    except Exception as e:
        return handle_api_error("cancel_order", e)

if __name__ == "__main__":
    # For local development, using uvicorn directly
    import uvicorn
    logger.info("Starting Kite Connect Orders MCP server...")
    # Make sure the app is referenced correctly, e.g., main:mcp.app for uvicorn command line
    # When running directly like this, it might need adjustment based on FastMCP internals
    # Typically, you'd run: uvicorn main:mcp.app --reload
    # This block is mostly for illustrative purposes if running the script directly.
    # uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
    print("MCP Server defined. Run with: uvicorn main:mcp.app --reload")
    print("Ensure KITE_API_KEY and KITE_ACCESS_TOKEN are set in your environment or .env file.")
