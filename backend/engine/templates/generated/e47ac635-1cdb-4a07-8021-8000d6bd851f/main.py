from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
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
    service_name="kite_connect_orders",
    description="MCP server for managing trading orders via the Kite Connect v3 API. Allows placing, modifying, cancelling, and retrieving orders and trades."
)

# Initialize Kite Connect Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit
    # raise ValueError("API Key and Access Token are required.")
    # For now, we allow it to proceed but the client init will likely fail or requests will be unauthorized

kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction).

    Args:
        params: Parameters for placing the order.

    Returns:
        A dictionary containing the 'order_id' if successful, or an error dictionary.
    """
    logger.info(f"Received request to place order: {params.dict(exclude_none=True)}")
    try:
        response_data = await kite_client.place_order_async(params)
        # Assuming the response structure contains {'data': {'order_id': '...'}}
        if isinstance(response_data, dict) and 'data' in response_data and 'order_id' in response_data['data']:
            order_id = response_data['data']['order_id']
            logger.info(f"Successfully placed order {order_id}")
            return OrderResponse(order_id=order_id).dict()
        else:
            logger.warning(f"Place order call succeeded but response format unexpected: {response_data}")
            # Return the raw response if format is not as expected but request didn't fail
            return {"status": "success", "data": response_data}

    except KiteConnectError as e:
        logger.error(f"Kite API error placing order: {e.code} - {e.message}", exc_info=True)
        return ErrorResponse(error_type=e.error_type, message=e.message, code=e.code).dict()
    except Exception as e:
        logger.error(f"Unexpected error placing order: {str(e)}", exc_info=True)
        return ErrorResponse(error_type="ServerError", message=str(e), code=500).dict()

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify an open or pending order.

    Args:
        params: Parameters for modifying the order.

    Returns:
        A dictionary containing the 'order_id' if successful, or an error dictionary.
    """
    logger.info(f"Received request to modify order {params.order_id}: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
    try:
        response_data = await kite_client.modify_order_async(params)
        # Assuming the response structure contains {'data': {'order_id': '...'}}
        if isinstance(response_data, dict) and 'data' in response_data and 'order_id' in response_data['data']:
            order_id = response_data['data']['order_id']
            logger.info(f"Successfully modified order {order_id}")
            return OrderResponse(order_id=order_id).dict()
        else:
            logger.warning(f"Modify order call succeeded but response format unexpected: {response_data}")
            # Return the raw response if format is not as expected but request didn't fail
            return {"status": "success", "data": response_data}

    except KiteConnectError as e:
        logger.error(f"Kite API error modifying order {params.order_id}: {e.code} - {e.message}", exc_info=True)
        return ErrorResponse(error_type=e.error_type, message=e.message, code=e.code).dict()
    except Exception as e:
        logger.error(f"Unexpected error modifying order {params.order_id}: {str(e)}", exc_info=True)
        return ErrorResponse(error_type="ServerError", message=str(e), code=500).dict()

if __name__ == "__main__":
    logger.info("Starting Kite Connect Orders MCP Server...")
    mcp.run()
