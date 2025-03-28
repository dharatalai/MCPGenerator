from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional, List
import logging
import os
from dotenv import load_dotenv
import httpx

from models import (
    PlaceOrderParams, ModifyOrderParams, CancelOrderParams,
    GetOrderHistoryParams, Order, OrderHistoryEntry,
    PlaceOrderResponse, ModifyOrderResponse, CancelOrderResponse,
    VarietyEnum
)
from client import AsyncKiteClient, KiteApiException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="ZerodhaKiteConnectOrders",
    description="Provides tools to interact with the Zerodha Kite Connect Orders API, allowing users to place, modify, cancel, and retrieve order and trade information."
)

# Initialize API Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    # Consider exiting or raising a configuration error depending on desired behavior
    # raise ValueError("API Key and Access Token are required.")
    # For now, initialize client but it will fail on requests

kite_client = AsyncKiteClient(api_key=api_key, access_token=access_token, base_url=base_url)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction)."""
    logger.info(f"Received place_order request: {params}")
    try:
        # Extract variety for path parameter, remove it from payload
        variety = params.variety
        payload = params.dict(exclude={'variety'}, exclude_unset=True)
        logger.debug(f"Placing order with variety '{variety}' and payload: {payload}")
        result = await kite_client.place_order(variety=variety, data=payload)
        logger.info(f"Order placed successfully: {result}")
        return PlaceOrderResponse(**result).dict()
    except KiteApiException as e:
        logger.error(f"Kite API Exception during place_order: {e}")
        return {"error": str(e), "details": e.details}
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during place_order: {e}")
        return {"error": f"HTTP error: {e.response.status_code}", "details": str(e.response.text)}
    except Exception as e:
        logger.exception(f"Unexpected error during place_order: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify attributes of a pending regular or cover order."""
    logger.info(f"Received modify_order request: {params}")
    try:
        # Extract path parameters, remove them from payload
        variety = params.variety
        order_id = params.order_id
        payload = params.dict(exclude={'variety', 'order_id'}, exclude_unset=True)
        logger.debug(f"Modifying order with variety '{variety}', order_id '{order_id}', payload: {payload}")
        result = await kite_client.modify_order(variety=variety, order_id=order_id, data=payload)
        logger.info(f"Order modified successfully: {result}")
        return ModifyOrderResponse(**result).dict()
    except KiteApiException as e:
        logger.error(f"Kite API Exception during modify_order: {e}")
        return {"error": str(e), "details": e.details}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during modify_order: {e}")
        return {"error": f"HTTP error: {e.response.status_code}", "details": str(e.response.text)}
    except Exception as e:
        logger.exception(f"Unexpected error during modify_order: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel a pending regular or cover order."""
    logger.info(f"Received cancel_order request: {params}")
    try:
        # Extract path parameters, remove them from payload (though payload is usually empty for DELETE)
        variety = params.variety
        order_id = params.order_id
        payload = params.dict(exclude={'variety', 'order_id'}, exclude_unset=True) # parent_order_id might be needed
        logger.debug(f"Cancelling order with variety '{variety}', order_id '{order_id}', payload: {payload}")
        result = await kite_client.cancel_order(variety=variety, order_id=order_id, data=payload)
        logger.info(f"Order cancelled successfully: {result}")
        return CancelOrderResponse(**result).dict()
    except KiteApiException as e:
        logger.error(f"Kite API Exception during cancel_order: {e}")
        return {"error": str(e), "details": e.details}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during cancel_order: {e}")
        return {"error": f"HTTP error: {e.response.status_code}", "details": str(e.response.text)}
    except Exception as e:
        logger.exception(f"Unexpected error during cancel_order: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}

@mcp.tool()
async def get_orders() -> List[Dict[str, Any]]:
    """Retrieve the list of all orders (open, pending, and executed) for the current trading day."""
    logger.info("Received get_orders request")
    try:
        orders_data = await kite_client.get_orders()
        logger.info(f"Retrieved {len(orders_data)} orders successfully.")
        # Validate and serialize each order
        return [Order(**order).dict() for order in orders_data]
    except KiteApiException as e:
        logger.error(f"Kite API Exception during get_orders: {e}")
        return [{"error": str(e), "details": e.details}] # Return error within a list as expected type is List
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during get_orders: {e}")
        return [{"error": f"HTTP error: {e.response.status_code}", "details": str(e.response.text)}]
    except Exception as e:
        logger.exception(f"Unexpected error during get_orders: {e}")
        return [{"error": "An unexpected error occurred", "details": str(e)}]

@mcp.tool()
async def get_order_history(params: GetOrderHistoryParams) -> List[Dict[str, Any]]:
    """Retrieve the history of states for a given order."""
    logger.info(f"Received get_order_history request for order_id: {params.order_id}")
    try:
        history_data = await kite_client.get_order_history(order_id=params.order_id)
        logger.info(f"Retrieved history for order {params.order_id} successfully.")
        # Validate and serialize each history entry
        return [OrderHistoryEntry(**entry).dict() for entry in history_data]
    except KiteApiException as e:
        logger.error(f"Kite API Exception during get_order_history: {e}")
        return [{"error": str(e), "details": e.details}]
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during get_order_history: {e}")
        return [{"error": f"HTTP error: {e.response.status_code}", "details": str(e.response.text)}]
    except Exception as e:
        logger.exception(f"Unexpected error during get_order_history: {e}")
        return [{"error": "An unexpected error occurred", "details": str(e)}]

if __name__ == "__main__":
    if not api_key or not access_token:
        print("ERROR: KITE_API_KEY and KITE_ACCESS_TOKEN environment variables are required.")
        print("Please create a .env file or set them in your environment.")
    else:
        print(f"Starting ZerodhaKiteConnectOrders MCP server...")
        print(f"Using Kite API Base URL: {base_url}")
        mcp.run()
