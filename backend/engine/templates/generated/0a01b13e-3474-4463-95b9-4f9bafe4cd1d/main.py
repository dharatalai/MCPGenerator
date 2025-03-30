import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteConnectError
from models import PlaceOrderParams, ModifyOrderParams, OrderIdResponse

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="ZerodhaKiteConnect",
    description="MCP Server for interacting with the Zerodha Kite Connect API (v3) to manage trading orders and retrieve trade information. Allows placing, modifying, cancelling orders, and fetching order history and trades."
)

# Initialize Kite Connect Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_API_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit if credentials are required at startup
    # raise ValueError("API Key and Access Token are required.")
    kite_client = None # Or handle appropriately
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
        logger.info("KiteConnectClient initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize KiteConnectClient")
        kite_client = None

@mcp.tool()
def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction).

    Args:
        params: Order placement parameters including variety, tradingsymbol, exchange, etc.

    Returns:
        Dictionary containing the order_id of the placed order or an error message.
    """
    if not kite_client:
        logger.error("Kite client not initialized. Cannot place order.")
        return {"error": "Kite client not initialized. Check credentials."}

    logger.info(f"Attempting to place order: {params.dict(exclude_none=True)}")
    try:
        result = kite_client.place_order(params)
        logger.info(f"Order placed successfully: {result}")
        # Ensure the response matches the OrderIdResponse model structure
        return OrderIdResponse(**result).dict()
    except KiteConnectError as e:
        logger.error(f"Kite API error placing order: {e}")
        return {"error": str(e), "error_type": e.__class__.__name__}
    except Exception as e:
        logger.exception("Unexpected error placing order")
        return {"error": f"An unexpected error occurred: {str(e)}", "error_type": "ServerError"}

@mcp.tool()
def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify attributes of a pending regular or cover order (CO).

    Args:
        params: Order modification parameters including variety, order_id, and fields to modify.

    Returns:
        Dictionary containing the order_id of the modified order or an error message.
    """
    if not kite_client:
        logger.error("Kite client not initialized. Cannot modify order.")
        return {"error": "Kite client not initialized. Check credentials."}

    logger.info(f"Attempting to modify order: {params.dict(exclude_none=True)}")
    try:
        result = kite_client.modify_order(params)
        logger.info(f"Order modified successfully: {result}")
        # Ensure the response matches the OrderIdResponse model structure
        return OrderIdResponse(**result).dict()
    except KiteConnectError as e:
        logger.error(f"Kite API error modifying order: {e}")
        return {"error": str(e), "error_type": e.__class__.__name__}
    except Exception as e:
        logger.exception("Unexpected error modifying order")
        return {"error": f"An unexpected error occurred: {str(e)}", "error_type": "ServerError"}


if __name__ == "__main__":
    if not kite_client:
        print("ERROR: Kite client could not be initialized. Please check logs and environment variables.")
    else:
        # Note: FastMCP doesn't have a direct run method like Flask/FastAPI.
        # You typically run it using a command like:
        # mcp run main:mcp --port 8000
        # This block is mostly for informational purposes or potential future direct run capabilities.
        print("MCP server defined. Run using: mcp run main:mcp --port <your_port>")
        # To run programmatically (if needed, requires uvicorn):
        # import uvicorn
        # uvicorn.run(mcp.build_app(), host="0.0.0.0", port=8000)
