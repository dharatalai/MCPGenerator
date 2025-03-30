from mcp.server.fastmcp import FastMCP
from typing import Dict, Optional, Literal
import logging
import os
from dotenv import load_dotenv

from client import KiteConnectClient, KiteConnectError
from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    OrderResponse,
    ErrorResponse
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="KiteConnectOrders",
    description="MCP service for managing trading orders (placing, modifying, cancelling) using the Kite Connect V3 API."
)

# Initialize Kite Connect Client
api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")
base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not api_key or not access_token:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    # Optionally raise an error or exit if credentials are required at startup
    # raise ValueError("API Key and Access Token are required.")
    kite_client = None # Keep running but tools will fail
else:
    try:
        kite_client = KiteConnectClient(api_key=api_key, access_token=access_token, base_url=base_url)
        logger.info("KiteConnectClient initialized successfully.")
    except Exception as e:
        logger.exception(f"Failed to initialize KiteConnectClient: {e}")
        kite_client = None

# --- MCP Tools ---

@mcp.tool()
async def place_order(
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'],
    tradingsymbol: str,
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'],
    transaction_type: Literal['BUY', 'SELL'],
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'],
    quantity: int,
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'],
    validity: Literal['DAY', 'IOC', 'TTL'],
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity_ttl: Optional[int] = None,
    iceberg_legs: Optional[int] = None,
    iceberg_quantity: Optional[int] = None,
    auction_number: Optional[str] = None,
    tag: Optional[str] = None
) -> Dict:
    """Place an order of a particular variety (regular, amo, co, iceberg, auction)."""
    if not kite_client:
        logger.error("place_order: KiteConnectClient is not initialized.")
        return ErrorResponse(error="Client not initialized. Check API Key/Token.").dict()

    try:
        params = PlaceOrderParams(
            variety=variety,
            tradingsymbol=tradingsymbol,
            exchange=exchange,
            transaction_type=transaction_type,
            order_type=order_type,
            quantity=quantity,
            product=product,
            validity=validity,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
            validity_ttl=validity_ttl,
            iceberg_legs=iceberg_legs,
            iceberg_quantity=iceberg_quantity,
            auction_number=auction_number,
            tag=tag
        )
        logger.info(f"Placing order with params: {params.dict(exclude_none=True)}")
        response_data = await kite_client.place_order(params)
        logger.info(f"Order placed successfully: {response_data}")
        # Assuming response_data is {'data': {'order_id': '...'}}
        order_id = response_data.get('data', {}).get('order_id')
        if order_id:
             return OrderResponse(order_id=order_id).dict()
        else:
             logger.error(f"Order placement succeeded but order_id not found in response: {response_data}")
             return ErrorResponse(error="Order placed but failed to retrieve order_id", details=response_data).dict()

    except KiteConnectError as e:
        logger.error(f"Kite API error during place_order: {e}")
        return ErrorResponse(error=e.__class__.__name__, message=str(e), details=e.details).dict()
    except Exception as e:
        logger.exception(f"Unexpected error during place_order: {e}")
        return ErrorResponse(error="InternalServerError", message=str(e)).dict()

@mcp.tool()
async def modify_order(
    variety: Literal['regular', 'co', 'amo', 'iceberg', 'auction'],
    order_id: str,
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = None,
    quantity: Optional[int] = None,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = None
) -> Dict:
    """Modify an open or pending order. Parameters depend on the order variety."""
    if not kite_client:
        logger.error("modify_order: KiteConnectClient is not initialized.")
        return ErrorResponse(error="Client not initialized. Check API Key/Token.").dict()

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
        logger.info(f"Modifying order {order_id} with params: {params.dict(exclude={'variety', 'order_id'}, exclude_none=True)}")
        response_data = await kite_client.modify_order(params)
        logger.info(f"Order modified successfully: {response_data}")
        # Assuming response_data is {'data': {'order_id': '...'}}
        modified_order_id = response_data.get('data', {}).get('order_id')
        if modified_order_id:
            return OrderResponse(order_id=modified_order_id).dict()
        else:
            logger.error(f"Order modification succeeded but order_id not found in response: {response_data}")
            return ErrorResponse(error="Order modified but failed to retrieve order_id", details=response_data).dict()

    except KiteConnectError as e:
        logger.error(f"Kite API error during modify_order: {e}")
        return ErrorResponse(error=e.__class__.__name__, message=str(e), details=e.details).dict()
    except Exception as e:
        logger.exception(f"Unexpected error during modify_order: {e}")
        return ErrorResponse(error="InternalServerError", message=str(e)).dict()

@mcp.tool()
async def cancel_order(
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'],
    order_id: str
) -> Dict:
    """Cancel an open or pending order."""
    if not kite_client:
        logger.error("cancel_order: KiteConnectClient is not initialized.")
        return ErrorResponse(error="Client not initialized. Check API Key/Token.").dict()

    try:
        params = CancelOrderParams(variety=variety, order_id=order_id)
        logger.info(f"Cancelling order {order_id} of variety {variety}")
        response_data = await kite_client.cancel_order(params)
        logger.info(f"Order cancelled successfully: {response_data}")
        # Assuming response_data is {'data': {'order_id': '...'}}
        cancelled_order_id = response_data.get('data', {}).get('order_id')
        if cancelled_order_id:
            return OrderResponse(order_id=cancelled_order_id).dict()
        else:
            logger.error(f"Order cancellation succeeded but order_id not found in response: {response_data}")
            return ErrorResponse(error="Order cancelled but failed to retrieve order_id", details=response_data).dict()

    except KiteConnectError as e:
        logger.error(f"Kite API error during cancel_order: {e}")
        return ErrorResponse(error=e.__class__.__name__, message=str(e), details=e.details).dict()
    except Exception as e:
        logger.exception(f"Unexpected error during cancel_order: {e}")
        return ErrorResponse(error="InternalServerError", message=str(e)).dict()

if __name__ == "__main__":
    if not kite_client:
        logger.warning("Kite Connect client failed to initialize. MCP server starting, but tools will likely fail.")
    logger.info("Starting KiteConnectOrders MCP server...")
    mcp.run()
