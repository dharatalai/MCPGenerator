import logging
import os
from typing import Dict, Any, Union

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient
from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams, SuccessResponse, ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- MCP Server Setup ---
SERVICE_NAME = "kite_connect_orders"
SERVICE_DESCRIPTION = "Provides tools to interact with the Kite Connect Orders API (v3) for placing, modifying, cancelling stock market orders. This MCP utilizes the pykiteconnect library."

mcp = FastMCP(
    service_name=SERVICE_NAME,
    description=SERVICE_DESCRIPTION,
    version="1.0.0"
)

# --- Kite Connect Client Initialization ---
try:
    kite_api_key = os.getenv("KITE_API_KEY")
    kite_access_token = os.getenv("KITE_ACCESS_TOKEN")
    if not kite_api_key or not kite_access_token:
        logger.error("KITE_API_KEY or KITE_ACCESS_TOKEN environment variables not set.")
        # Allow server to start but tools will fail if client is needed
        kite_client = None
    else:
        kite_client = KiteConnectClient(api_key=kite_api_key, access_token=kite_access_token)
except ValueError as e:
    logger.error(f"Failed to initialize Kite Client: {e}")
    kite_client = None
except Exception as e:
    logger.exception("An unexpected error occurred during Kite Client initialization.")
    kite_client = None

# --- MCP Tools Definition ---

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Place an order of a particular variety (regular, amo, co, iceberg, auction).
    Does not guarantee execution, only placement.

    Args:
        params: Parameters for placing the order.

    Returns:
        Dictionary containing the 'order_id' upon successful placement or an error message.
    """
    if kite_client is None:
        logger.error("place_order tool called, but Kite Client is not initialized.")
        return ErrorResponse(message="Kite client not initialized. Check environment variables.", error_type="ConfigurationError").dict()

    logger.info(f"Received place_order request: {params.dict(exclude_none=True)}")
    result = await kite_client.place_order_async(params)
    return result.dict()

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modify attributes of a pending regular or cover order (CO).

    Args:
        params: Parameters for modifying the order.

    Returns:
        Dictionary containing the 'order_id' of the modified order or an error message.
    """
    if kite_client is None:
        logger.error("modify_order tool called, but Kite Client is not initialized.")
        return ErrorResponse(message="Kite client not initialized. Check environment variables.", error_type="ConfigurationError").dict()

    logger.info(f"Received modify_order request: {params.dict(exclude_none=True)}")
    result = await kite_client.modify_order_async(params)
    return result.dict()

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """
    Cancel a pending order.

    Args:
        params: Parameters for cancelling the order.

    Returns:
        Dictionary containing the 'order_id' of the cancelled order or an error message.
    """
    if kite_client is None:
        logger.error("cancel_order tool called, but Kite Client is not initialized.")
        return ErrorResponse(message="Kite client not initialized. Check environment variables.", error_type="ConfigurationError").dict()

    logger.info(f"Received cancel_order request: {params.dict(exclude_none=True)}")
    result = await kite_client.cancel_order_async(params)
    return result.dict()

# --- Main Execution --- #
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Kite Connect Orders MCP server...")
    # To run: uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
    # The FastMCP object 'mcp' is the ASGI application
    uvicorn.run("main:mcp", host="0.0.0.0", port=8000, reload=True)
