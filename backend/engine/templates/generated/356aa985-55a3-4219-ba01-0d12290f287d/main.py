from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import logging
import os
from dotenv import load_dotenv

from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams, OrderResponse, ErrorResponse
from client import KiteConnectClient, KiteApiException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="Provides tools to interact with the Kite Connect Orders API, allowing users to place, modify, cancel, and retrieve stock market orders and trades via Zerodha's Kite platform."
)

# Initialize Kite Connect API Client
try:
    kite_client = KiteConnectClient()
except ValueError as e:
    logger.error(f"Failed to initialize KiteConnectClient: {e}")
    # Exit or handle appropriately if client initialization fails
    exit(1)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction).

    Args:
        params: Parameters for placing the order.

    Returns:
        A dictionary containing the 'order_id' of the successfully placed order or an error dictionary.
    """
    logger.info(f"Received place_order request with variety: {params.variety}, symbol: {params.tradingsymbol}")
    try:
        result = await kite_client.place_order(params)
        logger.info(f"Successfully placed order: {result.get('order_id')}")
        # Ensure the response matches the OrderResponse model if needed, or return raw dict
        # For simplicity, returning the dict directly as Kite API might have variations
        return result # Potentially wrap in OrderResponse(**result).dict()
    except KiteApiException as e:
        logger.error(f"Kite API error during place_order: {e}")
        return ErrorResponse(error=str(e), type=e.__class__.__name__).dict()
    except Exception as e:
        logger.exception(f"Unexpected error during place_order: {e}")
        return ErrorResponse(error="An unexpected server error occurred.", type="ServerError").dict()

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify attributes of a pending regular or CO order.

    Args:
        params: Parameters for modifying the order.

    Returns:
        A dictionary containing the 'order_id' of the successfully modified order or an error dictionary.
    """
    logger.info(f"Received modify_order request for order_id: {params.order_id}, variety: {params.variety}")
    try:
        result = await kite_client.modify_order(params)
        logger.info(f"Successfully modified order: {result.get('order_id')}")
        return result # Potentially wrap in OrderResponse(**result).dict()
    except KiteApiException as e:
        logger.error(f"Kite API error during modify_order: {e}")
        return ErrorResponse(error=str(e), type=e.__class__.__name__).dict()
    except Exception as e:
        logger.exception(f"Unexpected error during modify_order: {e}")
        return ErrorResponse(error="An unexpected server error occurred.", type="ServerError").dict()

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel a pending order.

    Args:
        params: Parameters for cancelling the order.

    Returns:
        A dictionary containing the 'order_id' of the successfully cancelled order or an error dictionary.
    """
    logger.info(f"Received cancel_order request for order_id: {params.order_id}, variety: {params.variety}")
    try:
        result = await kite_client.cancel_order(params)
        logger.info(f"Successfully cancelled order: {result.get('order_id')}")
        return result # Potentially wrap in OrderResponse(**result).dict()
    except KiteApiException as e:
        logger.error(f"Kite API error during cancel_order: {e}")
        return ErrorResponse(error=str(e), type=e.__class__.__name__).dict()
    except Exception as e:
        logger.exception(f"Unexpected error during cancel_order: {e}")
        return ErrorResponse(error="An unexpected server error occurred.", type="ServerError").dict()

if __name__ == "__main__":
    import uvicorn
    # Run the MCP server using uvicorn
    # Example: uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
    # The FastMCP object automatically creates a FastAPI app instance at mcp.app
    logger.info("Starting KiteConnectOrders MCP server...")
    # Note: Running directly like this is for development.
    # Use a proper ASGI server like uvicorn or hypercorn in production.
    uvicorn.run("main:mcp.app", host="0.0.0.0", port=8000, reload=True)
