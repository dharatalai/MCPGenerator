from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional, List
import logging
import os
from dotenv import load_dotenv
import httpx

# Import models and client
from models import (
    PlaceOrderInput, PlaceOrderResponse,
    ModifyOrderInput, ModifyOrderResponse,
    CancelOrderInput, CancelOrderResponse,
    GetOrdersInput, OrderDetails
)
from client import KiteConnectClient, KiteApiException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="MCP server for interacting with the Kite Connect Orders API (v3). Allows placing, modifying, cancelling, and retrieving orders and trades."
)

# Initialize Kite Connect Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit if credentials are required at startup
    # raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set")
    kite_client = None # Indicate client is not ready
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
        logger.info("KiteConnectClient initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize KiteConnectClient: {e}")
        kite_client = None

# --- MCP Tools --- 

@mcp.tool(description="Place an order of a particular variety (regular, amo, co, iceberg, auction).")
async def place_order(params: PlaceOrderInput) -> Dict[str, Any]:
    """Places a new order on Kite Connect."""
    if not kite_client:
        return {"error": "Kite Connect client not initialized. Check API Key/Access Token."}
    
    logger.info(f"Received place_order request: {params.dict(exclude_none=True)}")
    try:
        response_data = await kite_client.place_order(params)
        # Assuming the response structure is {'data': {'order_id': '...'}}
        order_id = response_data.get("data", {}).get("order_id")
        if order_id:
            result = PlaceOrderResponse(order_id=order_id)
            logger.info(f"Order placed successfully: {result.dict()}")
            return result.dict()
        else:
            logger.error(f"Place order response did not contain order_id: {response_data}")
            return {"error": "Failed to place order, unexpected response format.", "details": response_data}
    except KiteApiException as e:
        logger.error(f"Kite API error during place_order: {e}")
        return {"error": "Kite API Error", "details": str(e)}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during place_order: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        logger.error(f"Network error during place_order: {e}")
        return {"error": "Network Error", "details": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error during place_order: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}

@mcp.tool(description="Modify an open or pending order. Send only the parameters that need to be modified.")
async def modify_order(params: ModifyOrderInput) -> Dict[str, Any]:
    """Modifies an existing order on Kite Connect."""
    if not kite_client:
        return {"error": "Kite Connect client not initialized. Check API Key/Access Token."}

    logger.info(f"Received modify_order request for order_id {params.order_id}: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
    try:
        response_data = await kite_client.modify_order(params)
        # Assuming the response structure is {'data': {'order_id': '...'}}
        order_id = response_data.get("data", {}).get("order_id")
        if order_id:
            result = ModifyOrderResponse(order_id=order_id)
            logger.info(f"Order modified successfully: {result.dict()}")
            return result.dict()
        else:
            logger.error(f"Modify order response did not contain order_id: {response_data}")
            return {"error": "Failed to modify order, unexpected response format.", "details": response_data}
    except KiteApiException as e:
        logger.error(f"Kite API error during modify_order: {e}")
        return {"error": "Kite API Error", "details": str(e)}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during modify_order: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        logger.error(f"Network error during modify_order: {e}")
        return {"error": "Network Error", "details": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error during modify_order: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}

@mcp.tool(description="Cancel an open or pending order.")
async def cancel_order(params: CancelOrderInput) -> Dict[str, Any]:
    """Cancels an existing order on Kite Connect."""
    if not kite_client:
        return {"error": "Kite Connect client not initialized. Check API Key/Access Token."}

    logger.info(f"Received cancel_order request for order_id {params.order_id}: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
    try:
        response_data = await kite_client.cancel_order(params)
        # Assuming the response structure is {'data': {'order_id': '...'}}
        order_id = response_data.get("data", {}).get("order_id")
        if order_id:
            result = CancelOrderResponse(order_id=order_id)
            logger.info(f"Order cancelled successfully: {result.dict()}")
            return result.dict()
        else:
            logger.error(f"Cancel order response did not contain order_id: {response_data}")
            return {"error": "Failed to cancel order, unexpected response format.", "details": response_data}
    except KiteApiException as e:
        logger.error(f"Kite API error during cancel_order: {e}")
        return {"error": "Kite API Error", "details": str(e)}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during cancel_order: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        logger.error(f"Network error during cancel_order: {e}")
        return {"error": "Network Error", "details": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error during cancel_order: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}

@mcp.tool(description="Retrieve the list of all orders (open, pending, executed) for the current trading day.")
async def get_orders(params: GetOrdersInput = GetOrdersInput()) -> Dict[str, Any]:
    """Retrieves the list of orders for the day from Kite Connect."""
    if not kite_client:
        return {"error": "Kite Connect client not initialized. Check API Key/Access Token."}
    
    logger.info("Received get_orders request.")
    try:
        response_data = await kite_client.get_orders()
        # Assuming the response structure is {'data': [...]}
        orders_list = response_data.get("data")
        if isinstance(orders_list, list):
            # Validate and parse each order using Pydantic model
            validated_orders = [OrderDetails(**order).dict() for order in orders_list]
            logger.info(f"Retrieved {len(validated_orders)} orders successfully.")
            # MCP expects a dict response, wrap the list
            return {"orders": validated_orders}
        else:
            logger.error(f"Get orders response did not contain a list in 'data': {response_data}")
            return {"error": "Failed to get orders, unexpected response format.", "details": response_data}
    except KiteApiException as e:
        logger.error(f"Kite API error during get_orders: {e}")
        return {"error": "Kite API Error", "details": str(e)}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during get_orders: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        logger.error(f"Network error during get_orders: {e}")
        return {"error": "Network Error", "details": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error during get_orders: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}


if __name__ == "__main__":
    if not kite_client:
        print("ERROR: Kite Connect client failed to initialize. Check logs and environment variables.")
        print("MCP server cannot start without a functional client.")
    else:
        print("Starting KiteConnectOrders MCP Server...")
        mcp.run()
