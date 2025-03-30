from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import logging
import os
from dotenv import load_dotenv

from models import (PlaceOrderParams, ModifyOrderParams, CancelOrderParams, 
                    KiteApiError, OrderIDResponse)
from client import KiteConnectClient, KiteClientError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectTrading",
    description="MCP service providing tools to interact with the Kite Connect V3 trading API, focusing on order management. Allows placing, modifying, cancelling orders."
)

# Initialize API Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Consider raising an exception or exiting if credentials are required at startup
    # raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set")
    # For now, we allow it to proceed but client calls will likely fail

kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)

@mcp.tool(returns=OrderIDResponse)
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Places an order of a specified variety (regular, amo, co, iceberg, auction) 
    with the given parameters.
    """
    logger.info(f"Received place_order request: {params}")
    try:
        result = await kite_client.place_order(params)
        logger.info(f"Order placed successfully: {result}")
        return result
    except KiteClientError as e:
        logger.error(f"Error placing order: {e}", exc_info=True)
        # Return a structured error compatible with potential client expectations
        return KiteApiError(error_type=e.error_type, message=str(e)).dict()
    except Exception as e:
        logger.error(f"Unexpected error placing order: {e}", exc_info=True)
        return KiteApiError(error_type="GeneralException", message=f"An unexpected error occurred: {str(e)}").dict()

@mcp.tool(returns=OrderIDResponse)
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modifies specific attributes of an open or pending order.
    """
    logger.info(f"Received modify_order request: {params}")
    try:
        result = await kite_client.modify_order(params)
        logger.info(f"Order modified successfully: {result}")
        return result
    except KiteClientError as e:
        logger.error(f"Error modifying order: {e}", exc_info=True)
        return KiteApiError(error_type=e.error_type, message=str(e)).dict()
    except Exception as e:
        logger.error(f"Unexpected error modifying order: {e}", exc_info=True)
        return KiteApiError(error_type="GeneralException", message=f"An unexpected error occurred: {str(e)}").dict()

@mcp.tool(returns=OrderIDResponse)
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancels an open or pending order.
    """
    logger.info(f"Received cancel_order request: {params}")
    try:
        result = await kite_client.cancel_order(params)
        logger.info(f"Order cancelled successfully: {result}")
        return result
    except KiteClientError as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        return KiteApiError(error_type=e.error_type, message=str(e)).dict()
    except Exception as e:
        logger.error(f"Unexpected error cancelling order: {e}", exc_info=True)
        return KiteApiError(error_type="GeneralException", message=f"An unexpected error occurred: {str(e)}").dict()

if __name__ == "__main__":
    import uvicorn
    # Run the MCP server using uvicorn
    # Example: uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
    # The FastMCP object itself provides an app attribute compatible with ASGI servers
    logger.info("Starting KiteConnectTrading MCP server...")
    # Note: Running directly like this is mainly for development.
    # Use a proper ASGI server like uvicorn or hypercorn in production.
    # mcp.run() # This is a simplified run method, using uvicorn directly is more standard
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
