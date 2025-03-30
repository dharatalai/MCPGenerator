from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional
import logging
import os
from dotenv import load_dotenv

from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams, OrderResponse, ErrorResponse
from client import KiteConnectClient, KiteConnectError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectMCP",
    description="Provides tools to interact with the Kite Connect v3 API for managing trading orders and retrieving trade information. This MCP facilitates placing, modifying, canceling, and retrieving orders and trades."
)

# Initialize Kite Connect Client
# Ensure KITE_API_KEY and KITE_ACCESS_TOKEN are set in your environment or .env file
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")
    # Consider raising an exception or exiting if credentials are required at startup
    # raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set")
    kite_client = None # Client will not be functional
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
    except Exception as e:
        logger.error(f"Failed to initialize KiteConnectClient: {e}")
        kite_client = None

@mcp.tool()
def place_order(
    variety: str,
    tradingsymbol: str,
    exchange: str,
    transaction_type: str,
    order_type: str,
    quantity: int,
    product: str,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity: Optional[str] = "DAY",
    validity_ttl: Optional[int] = None,
    iceberg_legs: Optional[int] = None,
    iceberg_quantity: Optional[int] = None,
    auction_number: Optional[str] = None,
    tag: Optional[str] = None
) -> Dict[str, Any]:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction)."""
    if not kite_client:
        logger.error("KiteConnectClient is not initialized. Cannot place order.")
        return ErrorResponse(error="Client not initialized. Check API Key/Access Token.").dict()

    try:
        params = PlaceOrderParams(
            variety=variety,
            tradingsymbol=tradingsymbol,
            exchange=exchange,
            transaction_type=transaction_type,
            order_type=order_type,
            quantity=quantity,
            product=product,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
            validity=validity,
            validity_ttl=validity_ttl,
            iceberg_legs=iceberg_legs,
            iceberg_quantity=iceberg_quantity,
            auction_number=auction_number,
            tag=tag
        )
        logger.info(f"Attempting to place order: {params.dict(exclude_none=True)}")
        result = await kite_client.place_order(params)
        logger.info(f"Order placed successfully: {result}")
        # Ensure the response matches the expected OrderResponse structure
        if isinstance(result, dict) and 'data' in result and 'order_id' in result['data']:
             return OrderResponse(order_id=result['data']['order_id']).dict()
        else:
             logger.error(f"Unexpected response format from place_order: {result}")
             return ErrorResponse(error="Unexpected response format from API", details=str(result)).dict()

    except KiteConnectError as e:
        logger.error(f"Kite API Error placing order: {e}")
        return ErrorResponse(error=e.message, status_code=e.status_code, details=e.details).dict()
    except Exception as e:
        logger.exception(f"Unexpected error placing order: {e}")
        return ErrorResponse(error="An unexpected error occurred", details=str(e)).dict()

@mcp.tool()
def modify_order(
    variety: str,
    order_id: str,
    order_type: Optional[str] = None,
    quantity: Optional[int] = None,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity: Optional[str] = None
) -> Dict[str, Any]:
    """Modify attributes of a pending regular or cover order."""
    if not kite_client:
        logger.error("KiteConnectClient is not initialized. Cannot modify order.")
        return ErrorResponse(error="Client not initialized. Check API Key/Access Token.").dict()

    try:
        params = ModifyOrderParams(
            variety=variety,
            order_id=order_id,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
            validity=validity
        )
        logger.info(f"Attempting to modify order {order_id}: {params.dict(exclude={'order_id', 'variety'}, exclude_none=True)}")
        result = await kite_client.modify_order(params)
        logger.info(f"Order {order_id} modified successfully: {result}")
        # Ensure the response matches the expected OrderResponse structure
        if isinstance(result, dict) and 'data' in result and 'order_id' in result['data']:
             return OrderResponse(order_id=result['data']['order_id']).dict()
        else:
             logger.error(f"Unexpected response format from modify_order: {result}")
             return ErrorResponse(error="Unexpected response format from API", details=str(result)).dict()

    except KiteConnectError as e:
        logger.error(f"Kite API Error modifying order {order_id}: {e}")
        return ErrorResponse(error=e.message, status_code=e.status_code, details=e.details).dict()
    except Exception as e:
        logger.exception(f"Unexpected error modifying order {order_id}: {e}")
        return ErrorResponse(error="An unexpected error occurred", details=str(e)).dict()

@mcp.tool()
def cancel_order(
    variety: str,
    order_id: str,
    parent_order_id: Optional[str] = None
) -> Dict[str, Any]:
    """Cancel a pending order."""
    if not kite_client:
        logger.error("KiteConnectClient is not initialized. Cannot cancel order.")
        return ErrorResponse(error="Client not initialized. Check API Key/Access Token.").dict()

    try:
        params = CancelOrderParams(
            variety=variety,
            order_id=order_id,
            parent_order_id=parent_order_id
        )
        logger.info(f"Attempting to cancel order {order_id} (variety: {variety}, parent: {parent_order_id})")
        result = await kite_client.cancel_order(params)
        logger.info(f"Order {order_id} cancelled successfully: {result}")
        # Ensure the response matches the expected OrderResponse structure
        if isinstance(result, dict) and 'data' in result and 'order_id' in result['data']:
             return OrderResponse(order_id=result['data']['order_id']).dict()
        else:
             logger.error(f"Unexpected response format from cancel_order: {result}")
             return ErrorResponse(error="Unexpected response format from API", details=str(result)).dict()

    except KiteConnectError as e:
        logger.error(f"Kite API Error cancelling order {order_id}: {e}")
        return ErrorResponse(error=e.message, status_code=e.status_code, details=e.details).dict()
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order {order_id}: {e}")
        return ErrorResponse(error="An unexpected error occurred", details=str(e)).dict()


if __name__ == "__main__":
    # Example usage (for testing, replace with actual server run command)
    # You would typically run this with: uvicorn main:mcp.app --reload
    import uvicorn
    logger.info("Starting KiteConnectMCP server...")
    if not kite_client:
         logger.warning("Kite Client is not initialized due to missing credentials. API calls will fail.")
    uvicorn.run("main:mcp.app", host="0.0.0.0", port=8000, reload=True)
