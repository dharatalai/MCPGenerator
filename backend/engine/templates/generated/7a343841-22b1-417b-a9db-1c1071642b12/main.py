import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectAPIError, ZerodhaKiteConnectClient
from models import (
    CancelOrderParams,
    GetOrderHistoryParams,
    GetOrderTradesParams,
    ModifyRegularOrderParams,
    PlaceOrderParams,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="ZerodhaKiteConnect",
    description="MCP server for interacting with the Zerodha Kite Connect v3 Orders API. Allows placing, modifying, cancelling, and retrieving orders and trades.",
)

# Initialize API Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error(
        "KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables."
    )
    # Consider exiting or raising a configuration error
    # For now, we allow initialization but client calls will fail.
    api_client = None
else:
    try:
        api_client = ZerodhaKiteConnectClient(
            api_key=api_key, access_token=access_token, base_url=base_url
        )
        logger.info("ZerodhaKiteConnectClient initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize ZerodhaKiteConnectClient")
        api_client = None


def handle_api_error(tool_name: str, error: Exception) -> Dict[str, Any]:
    """Handles errors during API calls and returns a standardized error dict."""
    logger.error(f"Error in {tool_name}: {error}", exc_info=True)
    if isinstance(error, KiteConnectAPIError):
        return {
            "error": f"Kite API Error: {error.message}",
            "status_code": error.code,
            "details": str(error),
        }
    elif hasattr(error, "response") and error.response is not None:
        try:
            details = error.response.json()
        except Exception:
            details = error.response.text
        return {
            "error": f"HTTP Error: {error.response.status_code}",
            "details": details,
        }
    else:
        return {"error": f"An unexpected error occurred: {str(error)}"}


@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction)."""
    if not api_client:
        return {"error": "API client not initialized. Check environment variables."}
    try:
        logger.info(f"Placing order with params: {params.model_dump_json()}")
        result = await api_client.place_order(params)
        logger.info(f"Order placed successfully: {result}")
        return result
    except Exception as e:
        return handle_api_error("place_order", e)


@mcp.tool()
async def modify_order(params: ModifyRegularOrderParams) -> Dict[str, Any]:
    """Modify attributes of an open or pending regular or CO order."""
    if not api_client:
        return {"error": "API client not initialized. Check environment variables."}
    try:
        logger.info(f"Modifying order with params: {params.model_dump_json()}")
        result = await api_client.modify_order(params)
        logger.info(f"Order modified successfully: {result}")
        return result
    except Exception as e:
        return handle_api_error("modify_order", e)


@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel an open or pending order."""
    if not api_client:
        return {"error": "API client not initialized. Check environment variables."}
    try:
        logger.info(f"Cancelling order with params: {params.model_dump_json()}")
        result = await api_client.cancel_order(params)
        logger.info(f"Order cancelled successfully: {result}")
        return result
    except Exception as e:
        return handle_api_error("cancel_order", e)


@mcp.tool()
async def get_orders() -> Dict[str, Any]:
    """Retrieve the list of all orders for the current trading day."""
    if not api_client:
        return {"error": "API client not initialized. Check environment variables."}
    try:
        logger.info("Retrieving all orders.")
        result = await api_client.get_orders()
        logger.info(f"Retrieved {len(result.get('data', []))} orders.")
        return result
    except Exception as e:
        return handle_api_error("get_orders", e)


@mcp.tool()
async def get_order_history(params: GetOrderHistoryParams) -> Dict[str, Any]:
    """Retrieve the history (state transitions) of a given order."""
    if not api_client:
        return {"error": "API client not initialized. Check environment variables."}
    try:
        logger.info(f"Retrieving order history for order_id: {params.order_id}")
        result = await api_client.get_order_history(params.order_id)
        logger.info(
            f"Retrieved history for order {params.order_id}: {len(result.get('data', []))} states."
        )
        return result
    except Exception as e:
        return handle_api_error("get_order_history", e)


@mcp.tool()
async def get_trades() -> Dict[str, Any]:
    """Retrieve the list of all executed trades for the current trading day."""
    if not api_client:
        return {"error": "API client not initialized. Check environment variables."}
    try:
        logger.info("Retrieving all trades.")
        result = await api_client.get_trades()
        logger.info(f"Retrieved {len(result.get('data', []))} trades.")
        return result
    except Exception as e:
        return handle_api_error("get_trades", e)


@mcp.tool()
async def get_order_trades(params: GetOrderTradesParams) -> Dict[str, Any]:
    """Retrieve the trades generated by a specific order."""
    if not api_client:
        return {"error": "API client not initialized. Check environment variables."}
    try:
        logger.info(f"Retrieving trades for order_id: {params.order_id}")
        result = await api_client.get_order_trades(params.order_id)
        logger.info(
            f"Retrieved trades for order {params.order_id}: {len(result.get('data', []))} trades."
        )
        return result
    except Exception as e:
        return handle_api_error("get_order_trades", e)


if __name__ == "__main__":
    if not api_client:
        logger.critical(
            "API Client could not be initialized. MCP server cannot start without valid API credentials."
        )
    else:
        logger.info("Starting ZerodhaKiteConnect MCP server...")
        # Note: FastMCP().run() uses uvicorn.run() which might need host/port config
        # depending on deployment needs. Default is 127.0.0.1:8000
        mcp.run() # Add host="0.0.0.0", port=8001 etc. if needed
