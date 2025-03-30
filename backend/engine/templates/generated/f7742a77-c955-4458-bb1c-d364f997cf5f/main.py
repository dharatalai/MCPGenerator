from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional, List
import logging
import os
from dotenv import load_dotenv

from models import (
    PlaceOrderParams, ModifyOrderParams, CancelOrderParams,
    GetOrderHistoryParams, GetOrderTradesParams, Order, Trade,
    KiteApiErrorResponse
)
from client import KiteConnectClient, KiteConnectError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnect",
    description="MCP server providing access to the Zerodha Kite Connect trading API (v3). Allows placing, modifying, and cancelling orders, retrieving order history and trades, fetching instrument data, and managing mutual fund orders."
)

# Initialize Kite Connect API Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    # Optionally raise an error or exit if credentials are required at startup
    # raise ValueError("Kite Connect API credentials not found.")
    kite_client = None # Client will be unusable, tools will fail
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
        logger.info("KiteConnectClient initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize KiteConnectClient: {e}")
        kite_client = None

def handle_api_error(tool_name: str, error: Exception) -> KiteApiErrorResponse:
    """Handles errors raised by the KiteConnectClient."""
    logger.error(f"Error in {tool_name}: {error}", exc_info=True)
    if isinstance(error, KiteConnectError):
        return KiteApiErrorResponse(
            error_type=error.error_type,
            message=error.message,
            status_code=error.status_code
        )
    else:
        # General unexpected error
        return KiteApiErrorResponse(
            error_type="ServerError",
            message=f"An unexpected error occurred: {str(error)}"
        )

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction)."""
    if not kite_client:
        return handle_api_error("place_order", Exception("Kite client not initialized.")).dict()
    try:
        logger.info(f"Placing order with params: {params.dict(exclude_unset=True)}")
        # Exclude 'variety' from the payload as it's a path parameter
        payload = params.dict(exclude={'variety'}, exclude_unset=True)
        result = await kite_client.place_order(variety=params.variety, data=payload)
        logger.info(f"Order placed successfully: {result}")
        return result
    except Exception as e:
        return handle_api_error("place_order", e).dict()

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify attributes of a pending regular or cover order."""
    if not kite_client:
        return handle_api_error("modify_order", Exception("Kite client not initialized.")).dict()
    try:
        logger.info(f"Modifying order {params.order_id} ({params.variety}) with params: {params.dict(exclude={'variety', 'order_id'}, exclude_unset=True)}")
        # Exclude path parameters from payload
        payload = params.dict(exclude={'variety', 'order_id'}, exclude_unset=True)
        result = await kite_client.modify_order(variety=params.variety, order_id=params.order_id, data=payload)
        logger.info(f"Order modified successfully: {result}")
        return result
    except Exception as e:
        return handle_api_error("modify_order", e).dict()

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel a pending regular or cover order."""
    if not kite_client:
        return handle_api_error("cancel_order", Exception("Kite client not initialized.")).dict()
    try:
        logger.info(f"Cancelling order {params.order_id} ({params.variety}) with params: {params.dict(exclude={'variety', 'order_id'}, exclude_unset=True)}")
        # Exclude path parameters from payload, pass parent_order_id if present
        payload = {}
        if params.parent_order_id:
            payload['parent_order_id'] = params.parent_order_id

        result = await kite_client.cancel_order(variety=params.variety, order_id=params.order_id, data=payload)
        logger.info(f"Order cancelled successfully: {result}")
        return result
    except Exception as e:
        return handle_api_error("cancel_order", e).dict()

@mcp.tool()
async def get_orders() -> List[Dict[str, Any]]:
    """Retrieve the list of all orders (open, pending, executed) for the current trading day."""
    if not kite_client:
        # Returning an error object within the list to somewhat match expected structure
        return [handle_api_error("get_orders", Exception("Kite client not initialized.")).dict()]
    try:
        logger.info("Fetching all orders for the day.")
        result = await kite_client.get_orders()
        logger.info(f"Fetched {len(result)} orders.")
        # Attempt to parse into Order models, but return raw dicts as per spec
        # try:
        #     return [Order(**order_data).dict() for order_data in result]
        # except Exception as parse_error:
        #     logger.warning(f"Could not parse all orders into Order model: {parse_error}")
        return result # Return raw list of dicts
    except Exception as e:
        return [handle_api_error("get_orders", e).dict()]

@mcp.tool()
async def get_order_history(params: GetOrderHistoryParams) -> List[Dict[str, Any]]:
    """Retrieve the history of status changes for a given order."""
    if not kite_client:
        return [handle_api_error("get_order_history", Exception("Kite client not initialized.")).dict()]
    try:
        logger.info(f"Fetching order history for order_id: {params.order_id}")
        result = await kite_client.get_order_history(order_id=params.order_id)
        logger.info(f"Fetched {len(result)} history entries for order {params.order_id}.")
        # try:
        #     return [Order(**order_data).dict() for order_data in result]
        # except Exception as parse_error:
        #     logger.warning(f"Could not parse order history into Order model: {parse_error}")
        return result # Return raw list of dicts
    except Exception as e:
        return [handle_api_error("get_order_history", e).dict()]

@mcp.tool()
async def get_trades() -> List[Dict[str, Any]]:
    """Retrieve the list of all executed trades for the current trading day."""
    if not kite_client:
        return [handle_api_error("get_trades", Exception("Kite client not initialized.")).dict()]
    try:
        logger.info("Fetching all trades for the day.")
        result = await kite_client.get_trades()
        logger.info(f"Fetched {len(result)} trades.")
        # try:
        #     return [Trade(**trade_data).dict() for trade_data in result]
        # except Exception as parse_error:
        #     logger.warning(f"Could not parse all trades into Trade model: {parse_error}")
        return result # Return raw list of dicts
    except Exception as e:
        return [handle_api_error("get_trades", e).dict()]

@mcp.tool()
async def get_order_trades(params: GetOrderTradesParams) -> List[Dict[str, Any]]:
    """Retrieve the trades generated by a specific order."""
    if not kite_client:
        return [handle_api_error("get_order_trades", Exception("Kite client not initialized.")).dict()]
    try:
        logger.info(f"Fetching trades for order_id: {params.order_id}")
        result = await kite_client.get_order_trades(order_id=params.order_id)
        logger.info(f"Fetched {len(result)} trades for order {params.order_id}.")
        # try:
        #     return [Trade(**trade_data).dict() for trade_data in result]
        # except Exception as parse_error:
        #     logger.warning(f"Could not parse order trades into Trade model: {parse_error}")
        return result # Return raw list of dicts
    except Exception as e:
        return [handle_api_error("get_order_trades", e).dict()]


if __name__ == "__main__":
    import uvicorn
    # Run the MCP server using uvicorn
    # The MCP server exposes a FastAPI application at mcp.app
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
