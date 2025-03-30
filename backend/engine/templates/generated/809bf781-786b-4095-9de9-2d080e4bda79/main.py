from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Union
import logging
import os
from dotenv import load_dotenv
import asyncio

from models import PlaceOrderParams, ModifyOrderParams, OrderResponse, ErrorResponse
from client import KiteConnectClient, KiteConnectError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- MCP Server Initialization --- #

mcp = FastMCP(
    service_name="kite_connect_orders",
    description="MCP service for interacting with the Kite Connect Orders API (v3) to place and modify stock market orders."
)

# --- Global API Client --- #
# Initialize the client globally or manage its lifecycle if needed (e.g., startup/shutdown events)
kite_client: KiteConnectClient

@mcp.on_event("startup")
async def startup_event():
    global kite_client
    try:
        kite_client = KiteConnectClient()
        logger.info("Kite Connect client initialized successfully.")
    except ValueError as e:
        logger.error(f"Failed to initialize Kite Connect client: {e}")
        # Depending on the desired behavior, you might want to exit or prevent startup
        raise RuntimeError(f"Client initialization failed: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during Kite Connect client initialization.")
        raise RuntimeError("Unexpected error during client initialization") from e

@mcp.on_event("shutdown")
async def shutdown_event():
    global kite_client
    if kite_client:
        await kite_client.close()
        logger.info("Kite Connect client shut down gracefully.")

# --- MCP Tools --- #

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Places an order of a specified variety (regular, amo, co, iceberg, auction). Does not guarantee execution.

    Args:
        params (PlaceOrderParams): Parameters for placing the order.

    Returns:
        Dict[str, Any]: A dictionary containing the 'order_id' on success, or an error structure on failure.
    """
    logger.info(f"Received place_order request: {params.dict(exclude_none=True)}")
    try:
        result = await kite_client.place_order(params)
        return result.dict()
    except AttributeError:
        # Handle case where kite_client might not be initialized if startup failed
        logger.error("Kite client not available for place_order.")
        return ErrorResponse(message="Kite client not initialized.", error_type="ConfigurationError").dict()
    except Exception as e:
        # Catch any unexpected errors during the tool execution itself
        logger.exception("Unexpected error executing place_order tool.")
        return ErrorResponse(message=f"Internal server error: {str(e)}", error_type="InternalServerError").dict()

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modifies attributes of a pending order (e.g., quantity, price). For Cover Orders (CO), only trigger_price can be modified.

    Args:
        params (ModifyOrderParams): Parameters for modifying the order.

    Returns:
        Dict[str, Any]: A dictionary containing the 'order_id' on success (confirming modification), or an error structure on failure.
    """
    logger.info(f"Received modify_order request for order_id {params.order_id}: {params.dict(exclude={'order_id'}, exclude_none=True)}")
    try:
        result = await kite_client.modify_order(params)
        return result.dict()
    except AttributeError:
        logger.error("Kite client not available for modify_order.")
        return ErrorResponse(message="Kite client not initialized.", error_type="ConfigurationError").dict()
    except Exception as e:
        logger.exception(f"Unexpected error executing modify_order tool for order {params.order_id}.")
        return ErrorResponse(message=f"Internal server error: {str(e)}", error_type="InternalServerError").dict()


# --- Main Execution --- #

if __name__ == "__main__":
    # FastMCP automatically handles running the Uvicorn server
    # You might need to configure host and port if defaults are not suitable
    # Example: mcp.run(host="0.0.0.0", port=8000)
    mcp.run()
