import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteConnectError
from models import PlaceOrderParams, ModifyOrderParams, OrderResponse

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="Provides tools to manage trading orders (place, modify) using the Kite Connect API v3."
)

# Initialize Kite Connect Client
API_KEY = os.getenv("KITE_API_KEY")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
API_BASE_URL = os.getenv("KITE_API_BASE_URL", "https://api.kite.trade")

if not API_KEY or not ACCESS_TOKEN:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit if credentials are critical
    # raise ValueError("API Key and Access Token are required.")
    # For now, let it proceed but client initialization will likely fail later or be non-functional

kite_client = KiteConnectClient(api_key=API_KEY, access_token=ACCESS_TOKEN, base_url=API_BASE_URL)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Places an order of a specified variety (regular, amo, co, iceberg, auction).

    Args:
        params: Parameters for placing the order.

    Returns:
        A dictionary containing the 'order_id' of the successfully placed order or an error message.
    """
    logger.info(f"Attempting to place order: {params.tradingsymbol} {params.transaction_type} Qty: {params.quantity}")
    try:
        result = await kite_client.place_order_async(params)
        logger.info(f"Successfully placed order {result['order_id']} for {params.tradingsymbol}")
        # Ensure the response matches the expected Pydantic model
        return OrderResponse(**result).dict()
    except KiteConnectError as e:
        logger.error(f"Kite API error placing order for {params.tradingsymbol}: {e}")
        return {"error": str(e), "error_type": e.__class__.__name__}
    except Exception as e:
        logger.exception(f"Unexpected error placing order for {params.tradingsymbol}: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}", "error_type": "ServerError"}

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modifies attributes of a pending order (regular, co, amo, iceberg, auction).

    Args:
        params: Parameters for modifying the order.

    Returns:
        A dictionary containing the 'order_id' of the modified order or an error message.
    """
    logger.info(f"Attempting to modify order: {params.order_id} (Variety: {params.variety})")
    try:
        result = await kite_client.modify_order_async(params)
        logger.info(f"Successfully modified order {result['order_id']}")
        # Ensure the response matches the expected Pydantic model
        return OrderResponse(**result).dict()
    except KiteConnectError as e:
        logger.error(f"Kite API error modifying order {params.order_id}: {e}")
        return {"error": str(e), "error_type": e.__class__.__name__}
    except Exception as e:
        logger.exception(f"Unexpected error modifying order {params.order_id}: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}", "error_type": "ServerError"}

if __name__ == "__main__":
    if not API_KEY or not ACCESS_TOKEN:
        print("ERROR: KITE_API_KEY and KITE_ACCESS_TOKEN environment variables are not set.")
        print("Please create a .env file or set them in your environment.")
    else:
        logger.info(f"Starting KiteConnectOrders MCP server...")
        # Note: FastMCP's run() method handles the Uvicorn server startup.
        # You might need to adjust host and port if needed, e.g., mcp.run(host="0.0.0.0", port=8000)
        mcp.run()
