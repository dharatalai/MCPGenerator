import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteConnectError
from models import PlaceOrderParams, ModifyOrderParams

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="MCP service for managing trading orders (placing, modifying, cancelling, retrieving orders and trades) using the Kite Connect v3 API. This service allows interaction with the order management system of Zerodha's Kite platform."
)

# Initialize Kite Connect Client
try:
    kite_client = KiteConnectClient()
except ValueError as e:
    logger.error(f"Failed to initialize KiteConnectClient: {e}")
    # Exit or handle appropriately if client initialization fails
    exit(1)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Place an order of a specified variety (regular, amo, co, iceberg, auction).
    Returns the order_id upon successful placement.

    Args:
        params: Parameters for placing the order.

    Returns:
        A dictionary containing the status and the order_id of the placed order,
        or an error dictionary.
    """
    logger.info(f"Received place_order request: {params.dict(exclude_none=True)}")
    try:
        result = await kite_client.place_order(params)
        logger.info(f"place_order successful: {result}")
        return result
    except KiteConnectError as e:
        logger.error(f"KiteConnectError in place_order: {e}")
        return {"status": "error", "error_type": e.__class__.__name__, "message": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in place_order: {e}")
        return {"status": "error", "error_type": "ServerError", "message": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modify attributes of a pending regular or cover order (CO).

    Args:
        params: Parameters for modifying the order.

    Returns:
        A dictionary containing the status and the order_id of the modified order,
        or an error dictionary.
    """
    logger.info(f"Received modify_order request for order_id {params.order_id}: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
    try:
        result = await kite_client.modify_order(params)
        logger.info(f"modify_order successful: {result}")
        return result
    except KiteConnectError as e:
        logger.error(f"KiteConnectError in modify_order: {e}")
        return {"status": "error", "error_type": e.__class__.__name__, "message": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in modify_order: {e}")
        return {"status": "error", "error_type": "ServerError", "message": f"An unexpected error occurred: {str(e)}"}

if __name__ == "__main__":
    # This block is for running the server directly, e.g., for development
    # For production, use a command like: uvicorn main:mcp.app --host 0.0.0.0 --port 8000
    import uvicorn
    uvicorn.run(mcp.app, host="127.0.0.1", port=8000)
