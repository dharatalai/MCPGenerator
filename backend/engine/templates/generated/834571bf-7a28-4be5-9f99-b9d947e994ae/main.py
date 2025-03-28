from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List
import logging
import os
from dotenv import load_dotenv

from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    GetOrdersParams,
    OrderIDResponse,
    Order,
    KiteErrorResponse
)
from client import ZerodhaKiteClient, KiteApiException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="ZerodhaKiteConnectOrders",
    description="MCP service for managing orders (placing, modifying, cancelling, retrieving) and trades using the Zerodha Kite Connect v3 API."
)

# Initialize API Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    # Depending on the desired behavior, you might want to exit or raise an exception here.
    # For now, we'll let the client initialization fail if credentials are missing.

kite_client = ZerodhaKiteClient(api_key=api_key, access_token=access_token, base_url=base_url)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Place an order of a particular variety (regular, amo, co, iceberg, auction).

    Args:
        params: Order placement parameters.

    Returns:
        A dictionary containing the 'order_id' of the placed order or an error dictionary.
    """
    try:
        logger.info(f"Placing order with params: {params.dict(exclude_none=True)}")
        response_data = await kite_client.place_order(params)
        # Ensure the response format matches the expected OrderIDResponse
        if isinstance(response_data, dict) and "order_id" in response_data.get("data", {}):
             result = OrderIDResponse(order_id=response_data["data"]["order_id"])
             logger.info(f"Order placed successfully: {result.order_id}")
             return result.dict()
        else:
            logger.error(f"Unexpected response format from place_order: {response_data}")
            return KiteErrorResponse(error_type="UnexpectedResponse", message="Unexpected response format received from API.").dict()

    except KiteApiException as e:
        logger.error(f"API Error placing order: {e}")
        return KiteErrorResponse(error_type=e.error_type, message=e.message, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error placing order: {e}")
        return KiteErrorResponse(error_type="InternalServerError", message=str(e)).dict()

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modify an open or pending order.

    Args:
        params: Order modification parameters.

    Returns:
        A dictionary containing the 'order_id' of the modified order or an error dictionary.
    """
    try:
        logger.info(f"Modifying order {params.order_id} with params: {params.dict(exclude={'variety', 'order_id'}, exclude_none=True)}")
        response_data = await kite_client.modify_order(params)
        # Ensure the response format matches the expected OrderIDResponse
        if isinstance(response_data, dict) and "order_id" in response_data.get("data", {}):
            result = OrderIDResponse(order_id=response_data["data"]["order_id"])
            logger.info(f"Order modified successfully: {result.order_id}")
            return result.dict()
        else:
            logger.error(f"Unexpected response format from modify_order: {response_data}")
            return KiteErrorResponse(error_type="UnexpectedResponse", message="Unexpected response format received from API.").dict()

    except KiteApiException as e:
        logger.error(f"API Error modifying order: {e}")
        return KiteErrorResponse(error_type=e.error_type, message=e.message, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error modifying order: {e}")
        return KiteErrorResponse(error_type="InternalServerError", message=str(e)).dict()

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """
    Cancel an open or pending order.

    Args:
        params: Order cancellation parameters.

    Returns:
        A dictionary containing the 'order_id' of the cancelled order or an error dictionary.
    """
    try:
        logger.info(f"Cancelling order {params.order_id} (variety: {params.variety.value}) with parent_id: {params.parent_order_id}")
        response_data = await kite_client.cancel_order(params)
        # Ensure the response format matches the expected OrderIDResponse
        if isinstance(response_data, dict) and "order_id" in response_data.get("data", {}):
            result = OrderIDResponse(order_id=response_data["data"]["order_id"])
            logger.info(f"Order cancelled successfully: {result.order_id}")
            return result.dict()
        else:
            logger.error(f"Unexpected response format from cancel_order: {response_data}")
            return KiteErrorResponse(error_type="UnexpectedResponse", message="Unexpected response format received from API.").dict()

    except KiteApiException as e:
        logger.error(f"API Error cancelling order: {e}")
        return KiteErrorResponse(error_type=e.error_type, message=e.message, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order: {e}")
        return KiteErrorResponse(error_type="InternalServerError", message=str(e)).dict()

@mcp.tool()
async def get_orders(params: GetOrdersParams) -> Dict[str, Any]:
    """
    Retrieve the list of all orders (open, pending, executed) for the day.

    Args:
        params: Get orders parameters (currently empty).

    Returns:
        A dictionary containing a list of order objects or an error dictionary.
    """
    try:
        logger.info("Retrieving orders")
        orders_data = await kite_client.get_orders()
        # Basic validation: check if it's a list
        if isinstance(orders_data, list):
            # Attempt to parse each item into an Order model, logging errors for invalid items
            parsed_orders = []
            for order_item in orders_data:
                try:
                    # Ensure order_item is a dict before parsing
                    if isinstance(order_item, dict):
                        parsed_orders.append(Order(**order_item).dict())
                    else:
                         logger.warning(f"Skipping non-dict item in orders list: {order_item}")
                except Exception as parse_error:
                    logger.warning(f"Failed to parse order item: {order_item}. Error: {parse_error}")
                    # Optionally include partially parsed or raw data if needed

            logger.info(f"Retrieved {len(parsed_orders)} orders successfully.")
            return {"orders": parsed_orders} # Wrap the list in a dictionary
        else:
            logger.error(f"Unexpected response format from get_orders: {orders_data}")
            return KiteErrorResponse(error_type="UnexpectedResponse", message="Expected a list of orders, but received a different format.").dict()

    except KiteApiException as e:
        logger.error(f"API Error retrieving orders: {e}")
        return KiteErrorResponse(error_type=e.error_type, message=e.message, status_code=e.status_code).dict()
    except Exception as e:
        logger.exception(f"Unexpected error retrieving orders: {e}")
        return KiteErrorResponse(error_type="InternalServerError", message=str(e)).dict()


if __name__ == "__main__":
    # Note: FastMCP().run() starts the Uvicorn server.
    # You might need to configure host and port depending on your deployment.
    # Example: mcp.run(host="0.0.0.0", port=8000)
    mcp.run()
