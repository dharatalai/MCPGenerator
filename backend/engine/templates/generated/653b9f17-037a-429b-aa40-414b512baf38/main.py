import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteConnectError
from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="MCP server for interacting with the Kite Connect Orders API (v3). Allows placing, modifying, cancelling, and retrieving orders and trades."
)

# Initialize Kite Connect Client
API_KEY = os.getenv("KITE_API_KEY")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
BASE_URL = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not API_KEY or not ACCESS_TOKEN:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    exit(1)

kite_client = KiteConnectClient(api_key=API_KEY, access_token=ACCESS_TOKEN, base_url=BASE_URL)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Place an order of a particular variety (regular, amo, co, iceberg, auction).

    Args:
        params: Parameters for placing the order.

    Returns:
        Dictionary containing the status and the order_id of the placed order.
        Example: {'status': 'success', 'data': {'order_id': '151220000000000'}}
        On error, returns: {'error': 'Error message'}
    """
    logger.info(f"Received place_order request: {params.dict(exclude_none=True)}")
    try:
        result = await kite_client.place_order(params)
        logger.info(f"place_order successful: {result}")
        return result
    except KiteConnectError as e:
        logger.error(f"Error placing order: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("Unexpected error during place_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modify an open or pending order. Parameters depend on the order variety.

    Args:
        params: Parameters for modifying the order.

    Returns:
        Dictionary containing the status and the order_id of the modified order.
        Example: {'status': 'success', 'data': {'order_id': '151220000000000'}}
        On error, returns: {'error': 'Error message'}
    """
    logger.info(f"Received modify_order request: {params.dict(exclude_none=True)}")
    try:
        result = await kite_client.modify_order(params)
        logger.info(f"modify_order successful: {result}")
        return result
    except KiteConnectError as e:
        logger.error(f"Error modifying order: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("Unexpected error during modify_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """
    Cancel an open or pending order.

    Args:
        params: Parameters for cancelling the order.

    Returns:
        Dictionary containing the status and the order_id of the cancelled order.
        Example: {'status': 'success', 'data': {'order_id': '151220000000000'}}
        On error, returns: {'error': 'Error message'}
    """
    logger.info(f"Received cancel_order request: {params.dict(exclude_none=True)}")
    try:
        result = await kite_client.cancel_order(params)
        logger.info(f"cancel_order successful: {result}")
        return result
    except KiteConnectError as e:
        logger.error(f"Error cancelling order: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("Unexpected error during cancel_order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

if __name__ == "__main__":
    # For local development, run using uvicorn:
    # uvicorn main:mcp.app --reload --port 8000
    # The MCP server will be accessible according to FastMCP defaults.
    # This block is mainly for informational purposes as FastMCP handles its own entry point.
    logger.info("Starting KiteConnectOrders MCP Server.")
    logger.info("Run with: uvicorn main:mcp.app --host 0.0.0.0 --port 8000")
    # To run programmatically (though 'mcp.run()' is simpler for basic cases):
    # import uvicorn
    # uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
    pass # FastMCP's standard execution handles the server run.
