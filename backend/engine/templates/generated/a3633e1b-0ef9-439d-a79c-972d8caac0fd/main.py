import asyncio
import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteClientError
from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnect",
    description="Provides tools to interact with the Zerodha Kite Connect trading API (v3/v4 via pykiteconnect), allowing users to manage orders (place, modify, cancel, retrieve), fetch trades, get instrument lists, manage mutual fund orders, and potentially stream market data."
)

# Initialize Kite Connect Client
API_KEY = os.getenv("KITE_API_KEY")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")

if not API_KEY:
    logger.warning("KITE_API_KEY environment variable not set.")
if not ACCESS_TOKEN:
    logger.warning("KITE_ACCESS_TOKEN environment variable not set. Client will likely fail.")

kite_client = KiteConnectClient(api_key=API_KEY, access_token=ACCESS_TOKEN)

async def run_sync_in_executor(func, *args, **kwargs):
    """Runs a synchronous function in the default executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

@mcp.tool(description="Places an order of a specified variety (regular, amo, co, iceberg, auction).")
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Places a trading order using the Kite Connect API.

    Args:
        params: An object containing all necessary parameters for placing an order.

    Returns:
        A dictionary containing the 'order_id' on success, or an 'error' key on failure.
    """
    logger.info(f"Received place_order request: {params.dict(exclude_none=True)}")
    try:
        # pykiteconnect is synchronous, run it in an executor
        result = await run_sync_in_executor(
            kite_client.place_order,
            variety=params.variety.value,
            exchange=params.exchange.value,
            tradingsymbol=params.tradingsymbol,
            transaction_type=params.transaction_type.value,
            quantity=params.quantity,
            product=params.product.value,
            order_type=params.order_type.value,
            price=params.price,
            validity=params.validity.value if params.validity else None,
            disclosed_quantity=params.disclosed_quantity,
            trigger_price=params.trigger_price,
            tag=params.tag,
            iceberg_legs=params.iceberg_legs,
            iceberg_quantity=params.iceberg_quantity,
            auction_number=params.auction_number,
            validity_ttl=params.validity_ttl
        )
        logger.info(f"Order placed successfully: {result}")
        return result
    except KiteClientError as e:
        logger.error(f"Error placing order: {e}")
        return {"error": str(e), "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error during place_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool(description="Modifies attributes of a pending regular or cover order.")
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modifies an existing pending order.

    Args:
        params: An object containing the parameters for modifying the order.

    Returns:
        A dictionary containing the 'order_id' on success, or an 'error' key on failure.
    """
    logger.info(f"Received modify_order request: {params.dict(exclude_none=True)}")
    try:
        # pykiteconnect is synchronous, run it in an executor
        result = await run_sync_in_executor(
            kite_client.modify_order,
            variety=params.variety.value,
            order_id=params.order_id,
            parent_order_id=params.parent_order_id,
            quantity=params.quantity,
            price=params.price,
            order_type=params.order_type.value if params.order_type else None,
            trigger_price=params.trigger_price,
            validity=params.validity.value if params.validity else None,
            disclosed_quantity=params.disclosed_quantity
        )
        logger.info(f"Order modified successfully: {result}")
        return result
    except KiteClientError as e:
        logger.error(f"Error modifying order: {e}")
        return {"error": str(e), "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error during modify_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool(description="Cancels a pending regular or cover order.")
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """
    Cancels an existing pending order.

    Args:
        params: An object containing the parameters for cancelling the order.

    Returns:
        A dictionary containing the 'order_id' on success, or an 'error' key on failure.
    """
    logger.info(f"Received cancel_order request: {params.dict(exclude_none=True)}")
    try:
        # pykiteconnect is synchronous, run it in an executor
        result = await run_sync_in_executor(
            kite_client.cancel_order,
            variety=params.variety.value,
            order_id=params.order_id,
            parent_order_id=params.parent_order_id
        )
        logger.info(f"Order cancelled successfully: {result}")
        return result
    except KiteClientError as e:
        logger.error(f"Error cancelling order: {e}")
        return {"error": str(e), "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error during cancel_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

# Example of how to add other tools (implement client methods first)
# @mcp.tool(description="Retrieves the list of orders.")
# async def get_orders() -> List[Dict[str, Any]]:
#     logger.info("Received get_orders request")
#     try:
#         orders = await run_sync_in_executor(kite_client.get_orders)
#         logger.info(f"Retrieved {len(orders)} orders.")
#         return orders
#     except KiteClientError as e:
#         logger.error(f"Error getting orders: {e}")
#         return [{"error": str(e), "details": e.details}]
#     except Exception as e:
#         logger.exception("Unexpected error during get_orders")
#         return [{"error": f"An unexpected error occurred: {str(e)}"}]


if __name__ == "__main__":
    # Run the MCP server
    # Use uvicorn to run: uvicorn main:mcp --host 0.0.0.0 --port 8000
    logger.info("Starting KiteConnect MCP Server...")
    # The mcp.run() method is for development, use uvicorn in production
    # mcp.run() # This might block in some environments, use uvicorn command instead
    print("MCP Server defined. Run with: uvicorn main:mcp --host 0.0.0.0 --port 8000")
