from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List
import logging
import os
from dotenv import load_dotenv

# Import models and client
from models import (
    PlaceOrderParams, ModifyOrderParams, CancelOrderParams,
    GetOrdersParams, GetOrderHistoryParams,
    OrderResponse, Order, OrderHistoryEntry
)
from client import KiteConnectClient, KiteConnectError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="Provides tools to manage trading orders (place, modify, cancel, retrieve) using the Kite Connect v3 API."
)

# Initialize API Client
# Client initialization might raise ValueError if keys are missing
try:
    kite_client = KiteConnectClient()
except ValueError as e:
    logger.error(f"Failed to initialize KiteConnectClient: {e}")
    # Optionally exit or prevent server start if client can't be initialized
    raise SystemExit(f"Configuration Error: {e}")

# --- Define MCP Tools ---

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Places an order of a specified variety (regular, amo, co, iceberg, auction)."""
    logger.info(f"Received place_order request: {params.model_dump(exclude_unset=True)}")
    try:
        result: OrderResponse = await kite_client.place_order(params)
        logger.info(f"Successfully placed order: {result.order_id}")
        # Return the dictionary representation of the Pydantic model
        return result.model_dump()
    except KiteConnectError as e:
        logger.error(f"Kite API error during place_order: {e}")
        return {"error": str(e), "error_type": e.error_type, "status_code": e.status_code}
    except Exception as e:
        logger.exception("Unexpected error during place_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modifies attributes of an open or pending order."""
    logger.info(f"Received modify_order request for order_id {params.order_id}: {params.model_dump(exclude={'order_id', 'variety'}, exclude_unset=True)}")
    try:
        result: OrderResponse = await kite_client.modify_order(params)
        logger.info(f"Successfully modified order: {result.order_id}")
        return result.model_dump()
    except KiteConnectError as e:
        logger.error(f"Kite API error during modify_order: {e}")
        return {"error": str(e), "error_type": e.error_type, "status_code": e.status_code}
    except Exception as e:
        logger.exception("Unexpected error during modify_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancels an open or pending order."""
    logger.info(f"Received cancel_order request for order_id {params.order_id}")
    try:
        result: OrderResponse = await kite_client.cancel_order(params)
        logger.info(f"Successfully cancelled order: {result.order_id}")
        return result.model_dump()
    except KiteConnectError as e:
        logger.error(f"Kite API error during cancel_order: {e}")
        return {"error": str(e), "error_type": e.error_type, "status_code": e.status_code}
    except Exception as e:
        logger.exception("Unexpected error during cancel_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_orders(params: GetOrdersParams) -> Dict[str, Any]:
    """Retrieves the list of all orders (open, pending, executed) for the current trading day."""
    logger.info("Received get_orders request")
    try:
        orders: List[Order] = await kite_client.get_orders()
        logger.info(f"Successfully retrieved {len(orders)} orders.")
        # Convert list of Pydantic models to list of dicts
        return {"orders": [order.model_dump() for order in orders]}
    except KiteConnectError as e:
        logger.error(f"Kite API error during get_orders: {e}")
        return {"error": str(e), "error_type": e.error_type, "status_code": e.status_code}
    except Exception as e:
        logger.exception("Unexpected error during get_orders")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_order_history(params: GetOrderHistoryParams) -> Dict[str, Any]:
    """Retrieves the history of a specific order, showing its state transitions."""
    logger.info(f"Received get_order_history request for order_id {params.order_id}")
    try:
        history: List[OrderHistoryEntry] = await kite_client.get_order_history(params)
        logger.info(f"Successfully retrieved {len(history)} history entries for order {params.order_id}.")
        # Convert list of Pydantic models to list of dicts
        return {"history": [entry.model_dump() for entry in history]}
    except KiteConnectError as e:
        logger.error(f"Kite API error during get_order_history: {e}")
        return {"error": str(e), "error_type": e.error_type, "status_code": e.status_code}
    except Exception as e:
        logger.exception("Unexpected error during get_order_history")
        return {"error": f"An unexpected error occurred: {str(e)}"}

# --- Run the MCP Server ---
if __name__ == "__main__":
    # You would typically run this using uvicorn:
    # uvicorn main:mcp.app --reload --host 0.0.0.0 --port 8000
    # The mcp.run() method is for simpler, direct execution if needed (might not support reload)
    # For production, use a proper ASGI server like uvicorn or hypercorn.
    logger.info("Starting KiteConnectOrders MCP Server...")
    # mcp.run() # Use this for simple testing if needed
    print("Run the server using: uvicorn main:mcp.app --reload")
