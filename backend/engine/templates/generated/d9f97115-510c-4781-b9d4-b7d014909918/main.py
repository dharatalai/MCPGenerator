from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List
import logging
import os
from dotenv import load_dotenv

from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    GetOrderHistoryParams,
    KiteResponse,
    Order
)
from client import AsyncKiteClient, KiteApiException

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="ZerodhaKiteConnect",
    description="MCP server for interacting with the Zerodha Kite Connect API, focusing on order management and retrieval based on v3 documentation."
)

# Initialize API Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Optionally raise an error or exit, depending on desired behavior
    # raise ValueError("API Key and Access Token are required.")
    # For now, we allow it to proceed but client calls will likely fail

kite_client = AsyncKiteClient(api_key=api_key, access_token=access_token, base_url=base_url)

@mcp.tool()
async def place_order(params: PlaceOrderParams) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction).

    Args:
        params: Parameters for placing the order.

    Returns:
        A dictionary containing the 'order_id' of the placed order or an error message.
    """
    logger.info(f"Received request to place order: {params.dict(exclude_none=True)}")
    try:
        response = await kite_client.place_order(params)
        logger.info(f"Successfully placed order: {response}")
        # Ensure the response structure matches the expected KiteResponse or similar
        if isinstance(response, dict) and response.get("data") and isinstance(response["data"], dict) and "order_id" in response["data"]:
             return {"order_id": response["data"]["order_id"]}
        elif isinstance(response, dict):
             # Handle cases where the structure might differ slightly but contains the ID
             if "order_id" in response:
                 return {"order_id": response["order_id"]}
             else:
                 logger.warning(f"Place order response structure unexpected: {response}")
                 return {"warning": "Order placed, but response format unexpected.", "details": response}
        else:
            logger.error(f"Unexpected response type from place_order client: {type(response)}")
            return {"error": "Unexpected response format from API", "details": str(response)}

    except KiteApiException as e:
        logger.error(f"API error placing order: {e}")
        return {"error": e.message, "status_code": e.status_code, "error_type": e.error_type}
    except Exception as e:
        logger.exception("Unexpected error placing order")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def modify_order(params: ModifyOrderParams) -> Dict[str, Any]:
    """Modify attributes of a pending regular or cover order.

    Args:
        params: Parameters for modifying the order.

    Returns:
        A dictionary containing the 'order_id' of the modified order or an error message.
    """
    logger.info(f"Received request to modify order {params.order_id}: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
    try:
        response = await kite_client.modify_order(params)
        logger.info(f"Successfully modified order {params.order_id}: {response}")
        # Ensure the response structure matches the expected KiteResponse or similar
        if isinstance(response, dict) and response.get("data") and isinstance(response["data"], dict) and "order_id" in response["data"]:
             return {"order_id": response["data"]["order_id"]}
        elif isinstance(response, dict):
             # Handle cases where the structure might differ slightly but contains the ID
             if "order_id" in response:
                 return {"order_id": response["order_id"]}
             else:
                 logger.warning(f"Modify order response structure unexpected: {response}")
                 return {"warning": "Order modified, but response format unexpected.", "details": response}
        else:
            logger.error(f"Unexpected response type from modify_order client: {type(response)}")
            return {"error": "Unexpected response format from API", "details": str(response)}

    except KiteApiException as e:
        logger.error(f"API error modifying order {params.order_id}: {e}")
        return {"error": e.message, "status_code": e.status_code, "error_type": e.error_type}
    except Exception as e:
        logger.exception(f"Unexpected error modifying order {params.order_id}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def cancel_order(params: CancelOrderParams) -> Dict[str, Any]:
    """Cancel a pending regular, amo, co, iceberg, or auction order.

    Args:
        params: Parameters for cancelling the order.

    Returns:
        A dictionary containing the 'order_id' of the cancelled order or an error message.
    """
    logger.info(f"Received request to cancel order {params.order_id} (variety: {params.variety}) Parent: {params.parent_order_id}")
    try:
        response = await kite_client.cancel_order(params)
        logger.info(f"Successfully cancelled order {params.order_id}: {response}")
        # Ensure the response structure matches the expected KiteResponse or similar
        if isinstance(response, dict) and response.get("data") and isinstance(response["data"], dict) and "order_id" in response["data"]:
             return {"order_id": response["data"]["order_id"]}
        elif isinstance(response, dict):
             # Handle cases where the structure might differ slightly but contains the ID
             if "order_id" in response:
                 return {"order_id": response["order_id"]}
             else:
                 logger.warning(f"Cancel order response structure unexpected: {response}")
                 return {"warning": "Order cancelled, but response format unexpected.", "details": response}
        else:
            logger.error(f"Unexpected response type from cancel_order client: {type(response)}")
            return {"error": "Unexpected response format from API", "details": str(response)}

    except KiteApiException as e:
        logger.error(f"API error cancelling order {params.order_id}: {e}")
        return {"error": e.message, "status_code": e.status_code, "error_type": e.error_type}
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order {params.order_id}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_orders() -> Dict[str, Any]:
    """Retrieve the list of all orders (open, pending, executed) for the current trading day.

    Returns:
        A dictionary containing a list of orders or an error message.
    """
    logger.info("Received request to get orders")
    try:
        response = await kite_client.get_orders()
        logger.info(f"Successfully retrieved {len(response.get('data', [])) if isinstance(response, dict) else 'unknown number of'} orders.")
        # Assuming response is {'status': 'success', 'data': [list of orders]}
        if isinstance(response, dict) and response.get("status") == "success" and isinstance(response.get("data"), list):
            # Optionally validate each item against the Order model if needed
            return {"orders": response["data"]}
        else:
            logger.error(f"Unexpected response format from get_orders client: {response}")
            return {"error": "Unexpected response format from API", "details": str(response)}

    except KiteApiException as e:
        logger.error(f"API error getting orders: {e}")
        return {"error": e.message, "status_code": e.status_code, "error_type": e.error_type}
    except Exception as e:
        logger.exception("Unexpected error getting orders")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_order_history(params: GetOrderHistoryParams) -> Dict[str, Any]:
    """Retrieve the history (status changes) of a given order.

    Args:
        params: Parameters containing the order_id.

    Returns:
        A dictionary containing the order history or an error message.
    """
    logger.info(f"Received request to get order history for order_id: {params.order_id}")
    try:
        response = await kite_client.get_order_history(params)
        logger.info(f"Successfully retrieved history for order {params.order_id}")
        # Assuming response is {'status': 'success', 'data': [list of history items]}
        if isinstance(response, dict) and response.get("status") == "success" and isinstance(response.get("data"), list):
            return {"history": response["data"]}
        else:
            logger.error(f"Unexpected response format from get_order_history client: {response}")
            return {"error": "Unexpected response format from API", "details": str(response)}

    except KiteApiException as e:
        logger.error(f"API error getting order history for {params.order_id}: {e}")
        return {"error": e.message, "status_code": e.status_code, "error_type": e.error_type}
    except Exception as e:
        logger.exception(f"Unexpected error getting order history for {params.order_id}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    # Run the MCP server using uvicorn
    # The host and port can be configured as needed
    # Reload=True is useful for development
    uvicorn.run("main:mcp.app", host="0.0.0.0", port=8000, reload=True)
