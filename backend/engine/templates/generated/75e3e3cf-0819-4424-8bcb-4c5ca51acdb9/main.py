from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional, List
import logging
import os
from dotenv import load_dotenv

from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    GetOrderHistoryParams,
    OrderResponse,
    OrderDetails,
    OrderHistoryItem,
    ErrorResponse
)
from client import KiteConnectClient, KiteApiException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="MCP service for managing trading orders using the Kite Connect API v3. Allows placing, modifying, cancelling, and retrieving orders and trades."
)

# Initialize Kite Connect Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    # Optionally raise an error or exit if credentials are critical for startup
    # raise ValueError("Kite API credentials not found.")
    kite_client = None # Client will be unusable, tools will fail
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
        logger.info("KiteConnectClient initialized successfully.")
    except Exception as e:
        logger.exception(f"Failed to initialize KiteConnectClient: {e}")
        kite_client = None

# --- MCP Tools ---

@mcp.tool()
def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction)."""
    if not kite_client:
        return ErrorResponse(error="Kite client not initialized. Check credentials.").dict()
    try:
        logger.info(f"Placing order with params: {params.dict(exclude_none=True)}")
        result = kite_client.place_order(params)
        logger.info(f"Order placed successfully: {result}")
        # Assuming result is already Dict[str, str] like {'order_id': '...'}
        return result
    except KiteApiException as e:
        logger.error(f"Kite API error placing order: {e}")
        return ErrorResponse(error=str(e), error_type=e.error_type, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error placing order: {e}")
        return ErrorResponse(error=f"An unexpected error occurred: {e}").dict()

@mcp.tool()
def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify attributes of a pending regular or cover order."""
    if not kite_client:
        return ErrorResponse(error="Kite client not initialized. Check credentials.").dict()
    try:
        logger.info(f"Modifying order {params.order_id} with params: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
        result = kite_client.modify_order(params)
        logger.info(f"Order modified successfully: {result}")
        # Assuming result is already Dict[str, str] like {'order_id': '...'}
        return result
    except KiteApiException as e:
        logger.error(f"Kite API error modifying order: {e}")
        return ErrorResponse(error=str(e), error_type=e.error_type, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error modifying order: {e}")
        return ErrorResponse(error=f"An unexpected error occurred: {e}").dict()

@mcp.tool()
def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel a pending order."""
    if not kite_client:
        return ErrorResponse(error="Kite client not initialized. Check credentials.").dict()
    try:
        logger.info(f"Cancelling order {params.order_id} (variety: {params.variety}) with params: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
        result = kite_client.cancel_order(params)
        logger.info(f"Order cancelled successfully: {result}")
        # Assuming result is already Dict[str, str] like {'order_id': '...'}
        return result
    except KiteApiException as e:
        logger.error(f"Kite API error cancelling order: {e}")
        return ErrorResponse(error=str(e), error_type=e.error_type, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order: {e}")
        return ErrorResponse(error=f"An unexpected error occurred: {e}").dict()

@mcp.tool()
def get_orders() -> Dict[str, Any]:
    """Retrieve the list of all orders (open, pending, executed) for the current trading day."""
    if not kite_client:
        return ErrorResponse(error="Kite client not initialized. Check credentials.").dict()
    try:
        logger.info("Retrieving all orders for the day.")
        orders = kite_client.get_orders()
        logger.info(f"Retrieved {len(orders)} orders.")
        # Wrap the list in a dictionary for standard MCP response format
        return {"orders": orders}
    except KiteApiException as e:
        logger.error(f"Kite API error retrieving orders: {e}")
        return ErrorResponse(error=str(e), error_type=e.error_type, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error retrieving orders: {e}")
        return ErrorResponse(error=f"An unexpected error occurred: {e}").dict()

@mcp.tool()
def get_order_history(params: GetOrderHistoryParams) -> Dict[str, Any]:
    """Retrieve the history (various stages) of a given order."""
    if not kite_client:
        return ErrorResponse(error="Kite client not initialized. Check credentials.").dict()
    try:
        logger.info(f"Retrieving history for order ID: {params.order_id}")
        history = kite_client.get_order_history(params.order_id)
        logger.info(f"Retrieved {len(history)} history items for order {params.order_id}.")
        # Wrap the list in a dictionary for standard MCP response format
        return {"history": history}
    except KiteApiException as e:
        logger.error(f"Kite API error retrieving order history: {e}")
        return ErrorResponse(error=str(e), error_type=e.error_type, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error retrieving order history: {e}")
        return ErrorResponse(error=f"An unexpected error occurred: {e}").dict()


if __name__ == "__main__":
    # Example of how to run (requires uvicorn)
    # You would typically run this using: uvicorn main:mcp.app --reload
    logger.info("Starting KiteConnectOrders MCP server.")
    # mcp.run() # This might be blocking depending on FastMCP implementation
    # Instead, use uvicorn command line:
    print("Run the server using: uvicorn main:mcp.app --host 0.0.0.0 --port 8000")
    # For development: uvicorn main:mcp.app --reload
