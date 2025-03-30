import logging
import os
from typing import Dict, Any, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteConnectError
from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    GetOrdersParams,
    OrderIDResponse,
    Order
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    service_name="KiteConnectMCP",
    description="MCP server for interacting with the Kite Connect API, focusing on order management and retrieval functionalities. Allows placing, modifying, cancelling orders, and fetching order history and trades."
)

# Initialize Kite Connect Client
# Ensure KITE_API_KEY and KITE_ACCESS_TOKEN are set in your .env file or environment
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Exiting or raising an error might be appropriate in a real application
    # For this example, we'll proceed but the client will fail.
    kite_client = None
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
        logger.info("KiteConnectClient initialized successfully.")
    except Exception as e:
        logger.exception(f"Failed to initialize KiteConnectClient: {e}")
        kite_client = None

def handle_api_error(tool_name: str, error: Exception) -> Dict[str, Any]:
    """Handles errors from the KiteConnectClient."""
    logger.error(f"Error in {tool_name}: {error}", exc_info=True)
    if isinstance(error, KiteConnectError):
        return {"error": error.message, "status_code": error.status_code, "details": error.details}
    else:
        return {"error": f"An unexpected error occurred in {tool_name}: {str(error)}"}

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction)."""
    if not kite_client:
        return {"error": "KiteConnectClient not initialized. Check API keys."}
    try:
        logger.info(f"Placing order with params: {params.dict(exclude_none=True)}")
        result = await kite_client.place_order(params)
        logger.info(f"Order placed successfully: {result}")
        # Ensure the return type matches the expected Dict[str, str]
        # The client method already returns OrderIDResponse which is compatible
        return result.dict()
    except Exception as e:
        return handle_api_error("place_order", e)

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify an open or pending order."""
    if not kite_client:
        return {"error": "KiteConnectClient not initialized. Check API keys."}
    try:
        logger.info(f"Modifying order {params.order_id} ({params.variety}) with params: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
        result = await kite_client.modify_order(params)
        logger.info(f"Order modified successfully: {result}")
        return result.dict()
    except Exception as e:
        return handle_api_error("modify_order", e)

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel an open or pending order."""
    if not kite_client:
        return {"error": "KiteConnectClient not initialized. Check API keys."}
    try:
        logger.info(f"Cancelling order {params.order_id} ({params.variety}) with parent_order_id: {params.parent_order_id}")
        result = await kite_client.cancel_order(params)
        logger.info(f"Order cancelled successfully: {result}")
        return result.dict()
    except Exception as e:
        return handle_api_error("cancel_order", e)

@mcp.tool()
async def get_orders(params: GetOrdersParams = GetOrdersParams()) -> Dict[str, Any]:
    """Retrieve the list of all orders (open, pending, and executed) for the day."""
    # Note: GetOrdersParams is currently empty, added for future extensibility or consistency.
    if not kite_client:
        return {"error": "KiteConnectClient not initialized. Check API keys."}
    try:
        logger.info("Fetching orders.")
        orders: List[Order] = await kite_client.get_orders()
        logger.info(f"Fetched {len(orders)} orders.")
        # MCP tools typically return Dicts, so we wrap the list
        return {"orders": [order.dict() for order in orders]}
    except Exception as e:
        return handle_api_error("get_orders", e)

if __name__ == "__main__":
    if not kite_client:
        print("ERROR: Kite Connect client failed to initialize. Please check environment variables and logs.")
        print("MCP server will start, but tools will return errors.")
    # Add logic here to potentially wait for client initialization or handle it gracefully
    mcp.run()
