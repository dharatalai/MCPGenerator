from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Union
from pydantic import ValidationError
import logging
import os
from dotenv import load_dotenv

from models import PlaceOrderParams, ModifyOrderParams, OrderResponse, ErrorResponse
from client import KiteConnectClient, KiteConnectError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="Provides tools to manage trading orders (place, modify, cancel, retrieve) using the Kite Connect v3 API."
)

# Initialize Kite Connect Client
KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
KITE_API_BASE_URL = os.getenv("KITE_API_BASE_URL", "https://api.kite.trade")

if not KITE_API_KEY or not KITE_ACCESS_TOKEN:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit if credentials are required at startup
    # raise ValueError("Kite Connect credentials not found in environment variables.")
    kite_client = None # Allow server to start but tools will fail
else:
    try:
        kite_client = KiteConnectClient(
            api_key=KITE_API_KEY,
            access_token=KITE_ACCESS_TOKEN,
            base_url=KITE_API_BASE_URL
        )
    except ValueError as e:
        logger.error(f"Error initializing KiteConnectClient: {e}")
        kite_client = None

@mcp.startup
async def startup_event():
    logger.info("KiteConnectOrders MCP Server starting up.")
    # You could potentially add a check here to ensure the client is initialized
    if kite_client is None:
        logger.warning("KiteConnectClient is not initialized. API calls will fail.")

@mcp.shutdown
async def shutdown_event():
    if kite_client:
        await kite_client.close()
    logger.info("KiteConnectOrders MCP Server shutting down.")

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Union[OrderResponse, ErrorResponse]:
    """Place an order of a specific variety (regular, amo, co, iceberg, auction)."""
    if kite_client is None:
        logger.error("place_order tool called but Kite client is not initialized.")
        return ErrorResponse(error="Client not initialized due to missing credentials.")
    
    try:
        logger.info(f"Received place_order request with params: {params.dict()}")
        result = await kite_client.place_order(params)
        logger.info(f"Successfully placed order: {result.order_id}")
        return result
    except KiteConnectError as e:
        logger.error(f"Kite API error during place_order: {e.message}", exc_info=True)
        return ErrorResponse(error=f"Kite API Error ({e.status_code}): {e.message}", details=e.details)
    except ValidationError as e:
        logger.error(f"Validation error in place_order parameters: {e}", exc_info=True)
        return ErrorResponse(error="Input validation failed", details=e.errors())
    except Exception as e:
        logger.error(f"Unexpected error during place_order: {str(e)}", exc_info=True)
        return ErrorResponse(error=f"An unexpected error occurred: {str(e)}")

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Union[OrderResponse, ErrorResponse]:
    """Modify an open or pending order of a given variety."""
    if kite_client is None:
        logger.error("modify_order tool called but Kite client is not initialized.")
        return ErrorResponse(error="Client not initialized due to missing credentials.")
        
    try:
        logger.info(f"Received modify_order request with params: {params.dict()}")
        result = await kite_client.modify_order(params)
        logger.info(f"Successfully modified order: {result.order_id}")
        return result
    except KiteConnectError as e:
        logger.error(f"Kite API error during modify_order: {e.message}", exc_info=True)
        return ErrorResponse(error=f"Kite API Error ({e.status_code}): {e.message}", details=e.details)
    except ValidationError as e:
        logger.error(f"Validation error in modify_order parameters: {e}", exc_info=True)
        return ErrorResponse(error="Input validation failed", details=e.errors())
    except Exception as e:
        logger.error(f"Unexpected error during modify_order: {str(e)}", exc_info=True)
        return ErrorResponse(error=f"An unexpected error occurred: {str(e)}")

# Example of how to run the server directly (though usually done via uvicorn command)
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server using uvicorn...")
    # Note: Running directly might have issues with hot-reloading compared to CLI
    uvicorn.run(mcp, host="0.0.0.0", port=8000)
