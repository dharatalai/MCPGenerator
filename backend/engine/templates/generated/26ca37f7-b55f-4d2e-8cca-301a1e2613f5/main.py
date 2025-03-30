import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteConnectError
from models import CancelOrderParams, ModifyOrderParams, PlaceOrderParams, OrderResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="MCP server for managing trading orders (placing, modifying, cancelling) via the Kite Connect API v3."
)

# Initialize Kite Connect Client
API_KEY = os.getenv("KITE_API_KEY")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
BASE_URL = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not API_KEY or not ACCESS_TOKEN:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit if credentials are critical for startup
    # raise ValueError("API Key and Access Token are required.")
    # For now, we allow startup but client calls will fail.
    kite_client = None
else:
    try:
        kite_client = KiteConnectClient(api_key=API_KEY, access_token=ACCESS_TOKEN, base_url=BASE_URL)
        logger.info("KiteConnectClient initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize KiteConnectClient")
        kite_client = None

# --- MCP Tools ---

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Place an order of a particular variety (regular, amo, co, iceberg, auction).

    Args:
        params: Order placement parameters including variety, tradingsymbol, exchange, etc.

    Returns:
        A dictionary containing the 'order_id' upon success, or an error dictionary.
    """
    if not kite_client:
        logger.error("place_order: KiteConnectClient is not initialized.")
        return {"status": "error", "message": "Kite Connect client not initialized. Check credentials."}

    logger.info(f"Attempting to place order: {params.dict(exclude_unset=True)}")
    try:
        response_data = await kite_client.place_order_async(params)
        logger.info(f"Successfully placed order: {response_data}")
        # Assuming the API returns {'status': 'success', 'data': {'order_id': '...'}}
        if isinstance(response_data, dict) and response_data.get("status") == "success":
             # Validate and return using Pydantic model if desired, or return raw dict
            return response_data
        else:
            # Handle unexpected success response format
            logger.warning(f"Received unexpected success response format: {response_data}")
            return {"status": "success", "data": response_data} # Return raw data

    except KiteConnectError as e:
        logger.error(f"Kite API error placing order: {e}")
        return {"status": "error", "message": str(e), "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error placing order")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modify an open or pending order of a particular variety (regular, co).

    Args:
        params: Order modification parameters including variety, order_id, and fields to modify.

    Returns:
        A dictionary containing the 'order_id' upon success, or an error dictionary.
    """
    if not kite_client:
        logger.error("modify_order: KiteConnectClient is not initialized.")
        return {"status": "error", "message": "Kite Connect client not initialized. Check credentials."}

    logger.info(f"Attempting to modify order {params.order_id}: {params.dict(exclude={'order_id', 'variety'}, exclude_unset=True)}")
    try:
        response_data = await kite_client.modify_order_async(params)
        logger.info(f"Successfully modified order {params.order_id}: {response_data}")
        if isinstance(response_data, dict) and response_data.get("status") == "success":
            return response_data
        else:
            logger.warning(f"Received unexpected success response format for modify: {response_data}")
            return {"status": "success", "data": response_data}

    except KiteConnectError as e:
        logger.error(f"Kite API error modifying order {params.order_id}: {e}")
        return {"status": "error", "message": str(e), "details": e.details}
    except Exception as e:
        logger.exception(f"Unexpected error modifying order {params.order_id}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """
    Cancel an open or pending order.

    Args:
        params: Order cancellation parameters including variety and order_id.

    Returns:
        A dictionary containing the 'order_id' upon success, or an error dictionary.
    """
    if not kite_client:
        logger.error("cancel_order: KiteConnectClient is not initialized.")
        return {"status": "error", "message": "Kite Connect client not initialized. Check credentials."}

    logger.info(f"Attempting to cancel order {params.order_id} (variety: {params.variety})")
    try:
        response_data = await kite_client.cancel_order_async(params)
        logger.info(f"Successfully cancelled order {params.order_id}: {response_data}")
        if isinstance(response_data, dict) and response_data.get("status") == "success":
            return response_data
        else:
            logger.warning(f"Received unexpected success response format for cancel: {response_data}")
            return {"status": "success", "data": response_data}

    except KiteConnectError as e:
        logger.error(f"Kite API error cancelling order {params.order_id}: {e}")
        return {"status": "error", "message": str(e), "details": e.details}
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order {params.order_id}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting KiteConnectOrders MCP server...")
    # Run with uvicorn. Note: For production, consider using a process manager like Gunicorn.
    # The host and port can be configured via environment variables or command-line arguments if needed.
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
