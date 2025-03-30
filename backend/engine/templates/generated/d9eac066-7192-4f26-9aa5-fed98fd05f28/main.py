import logging
import os
from typing import Dict, Any, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteConnectError
from models import (PlaceOrderParams, ModifyOrderParams, CancelOrderParams,
                    GetOrdersParams, OrderResponse, OrderHistoryResponse)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP
mcp = FastMCP(
    service_name="KiteConnect",
    description="MCP server for Zerodha Kite Connect API, enabling interaction with trading functionalities like placing orders, retrieving order/trade history, fetching instrument data, and managing mutual fund orders. It utilizes the official pykiteconnect library."
)

# Initialize Kite Connect Client
try:
    kite_client = KiteConnectClient()
    logger.info("KiteConnect client initialized successfully.")
except KiteConnectError as e:
    logger.error(f"Failed to initialize KiteConnect client: {e}")
    # Exit or handle initialization failure appropriately
    exit(1)
except Exception as e:
    logger.error(f"An unexpected error occurred during client initialization: {e}")
    exit(1)

@mcp.tool()
def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place a trading order (regular, AMO, CO, Iceberg, Auction)."""
    try:
        logger.info(f"Placing order with params: {params.dict(exclude_none=True)}")
        order_result = kite_client.place_order(
            variety=params.variety,
            exchange=params.exchange,
            tradingsymbol=params.tradingsymbol,
            transaction_type=params.transaction_type,
            quantity=params.quantity,
            product=params.product,
            order_type=params.order_type,
            price=params.price,
            validity=params.validity,
            disclosed_quantity=params.disclosed_quantity,
            trigger_price=params.trigger_price,
            iceberg_legs=params.iceberg_legs,
            iceberg_quantity=params.iceberg_quantity,
            auction_number=params.auction_number,
            tag=params.tag,
            validity_ttl=params.validity_ttl
        )
        logger.info(f"Order placed successfully: {order_result}")
        return OrderResponse(**order_result).dict()
    except KiteConnectError as e:
        logger.error(f"Error placing order: {e}")
        return {"error": str(e), "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error placing order")
        return {"error": "An unexpected error occurred.", "details": str(e)}

@mcp.tool()
def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify a pending regular or cover order."""
    try:
        logger.info(f"Modifying order {params.order_id} with params: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
        modify_result = kite_client.modify_order(
            variety=params.variety,
            order_id=params.order_id,
            parent_order_id=params.parent_order_id,
            quantity=params.quantity,
            price=params.price,
            order_type=params.order_type,
            trigger_price=params.trigger_price,
            validity=params.validity,
            disclosed_quantity=params.disclosed_quantity
        )
        logger.info(f"Order modified successfully: {modify_result}")
        return OrderResponse(**modify_result).dict()
    except KiteConnectError as e:
        logger.error(f"Error modifying order {params.order_id}: {e}")
        return {"error": str(e), "details": e.details}
    except Exception as e:
        logger.exception(f"Unexpected error modifying order {params.order_id}")
        return {"error": "An unexpected error occurred.", "details": str(e)}

@mcp.tool()
def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel a pending regular, AMO, CO, Iceberg, or Auction order."""
    try:
        logger.info(f"Cancelling order {params.order_id} (variety: {params.variety})")
        cancel_result = kite_client.cancel_order(
            variety=params.variety,
            order_id=params.order_id,
            parent_order_id=params.parent_order_id
        )
        logger.info(f"Order cancelled successfully: {cancel_result}")
        return OrderResponse(**cancel_result).dict()
    except KiteConnectError as e:
        logger.error(f"Error cancelling order {params.order_id}: {e}")
        return {"error": str(e), "details": e.details}
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order {params.order_id}")
        return {"error": "An unexpected error occurred.", "details": str(e)}

@mcp.tool()
def get_orders(params: GetOrdersParams) -> Dict[str, Any]: # Keep params for potential future filtering
    """Retrieve the list of all orders (open, pending, executed) for the current trading day."""
    try:
        logger.info("Fetching orders")
        orders = kite_client.get_orders()
        logger.info(f"Fetched {len(orders)} orders successfully.")
        # Ensure the response matches the expected structure if needed
        # For now, return the raw list as KiteConnect provides it within a dict
        return OrderHistoryResponse(orders=orders).dict()
    except KiteConnectError as e:
        logger.error(f"Error fetching orders: {e}")
        return {"error": str(e), "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error fetching orders")
        return {"error": "An unexpected error occurred.", "details": str(e)}

# Example of how to run the server (e.g., using uvicorn)
# uvicorn main:mcp.app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting KiteConnect MCP server...")
    # MCP exposes a FastAPI app instance at mcp.app
    uvicorn.run(mcp.app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
