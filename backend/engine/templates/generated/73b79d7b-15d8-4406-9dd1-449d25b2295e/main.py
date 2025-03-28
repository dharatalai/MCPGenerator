import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import KiteConnectClient, KiteApiException
from models import PlaceOrderParams, ModifyOrderParams

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
SERVICE_NAME = "ZerodhaKiteConnectOrders"
DESCRIPTION = "Provides tools to manage trading orders (place, modify) using the Zerodha Kite Connect v3 API."

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
KITE_BASE_URL = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

if not KITE_API_KEY or not KITE_ACCESS_TOKEN:
    logger.error("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables or .env file.")
    exit(1)

# --- Initialize MCP and API Client ---
mcp = FastMCP(SERVICE_NAME, description=DESCRIPTION)
kite_client = KiteConnectClient(
    api_key=KITE_API_KEY,
    access_token=KITE_ACCESS_TOKEN,
    base_url=KITE_BASE_URL
)

# --- Define MCP Tools ---

@mcp.tool()
async def place_order(
    variety: str,
    tradingsymbol: str,
    exchange: str,
    transaction_type: str,
    order_type: str,
    quantity: int,
    product: str,
    validity: str,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity_ttl: Optional[int] = None,
    iceberg_legs: Optional[int] = None,
    iceberg_quantity: Optional[int] = None,
    auction_number: Optional[str] = None,
    tag: Optional[str] = None
) -> Dict[str, str]:
    """Places an order of a specified variety (regular, amo, co, iceberg, auction).

    Args:
        variety: Order variety (regular, amo, co, iceberg, auction). This will be part of the URL path.
        tradingsymbol: Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY23JUL18000CE').
        exchange: Name of the exchange (e.g., NSE, BSE, NFO, CDS, BCD, MCX).
        transaction_type: Transaction type: 'BUY' or 'SELL'.
        order_type: Order type: 'MARKET', 'LIMIT', 'SL', 'SL-M'.
        quantity: Quantity to transact.
        product: Product type: 'CNC', 'NRML', 'MIS', 'MTF'.
        validity: Order validity: 'DAY', 'IOC', 'TTL'.
        price: The price for LIMIT orders.
        trigger_price: The trigger price for SL, SL-M orders. Also used for CO.
        disclosed_quantity: Quantity to disclose publicly (for equity trades).
        validity_ttl: Order life span in minutes for TTL validity orders.
        iceberg_legs: Total number of legs for iceberg order type (2-10). Required for variety='iceberg'.
        iceberg_quantity: Split quantity for each iceberg leg (quantity/iceberg_legs). Required for variety='iceberg'.
        auction_number: Unique identifier for a specific auction. Required for variety='auction'.
        tag: Optional tag for the order (alphanumeric, max 20 chars).

    Returns:
        A dictionary containing the 'order_id' of the placed order upon success.
    """
    logger.info(f"Received place_order request for {tradingsymbol}")
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
        result = await kite_client.place_order(params)
        logger.info(f"Successfully placed order {result.get('order_id')}")
        return result
    except KiteApiException as e:
        logger.error(f"Kite API error during place_order: {e}")
        # Propagate API specific errors for better client handling
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during place_order: {e}")
        # Raise a generic exception for unexpected errors
        raise RuntimeError(f"An unexpected error occurred: {e}")

@mcp.tool()
async def modify_order(
    variety: str,
    order_id: str,
    parent_order_id: Optional[str] = None,
    order_type: Optional[str] = None,
    quantity: Optional[int] = None,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity: Optional[str] = None
) -> Dict[str, str]:
    """Modifies attributes of a pending regular or cover order.

    Args:
        variety: Variety of the order to modify (e.g., 'regular', 'co'). Path parameter.
        order_id: The ID of the order to modify. Path parameter.
        parent_order_id: ID of the parent order (required for modifying second-leg CO orders).
        order_type: New order type (e.g., 'LIMIT', 'MARKET').
        quantity: New quantity.
        price: New price (for LIMIT orders).
        trigger_price: New trigger price (for SL, SL-M, CO orders).
        disclosed_quantity: New disclosed quantity.
        validity: New validity ('DAY', 'IOC').

    Returns:
        A dictionary containing the 'order_id' of the modified order upon success.
    """
    logger.info(f"Received modify_order request for order_id {order_id}")
    try:
        params = ModifyOrderParams(
            variety=variety,
            order_id=order_id,
            parent_order_id=parent_order_id,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
            validity=validity
        )
        result = await kite_client.modify_order(params)
        logger.info(f"Successfully modified order {result.get('order_id')}")
        return result
    except KiteApiException as e:
        logger.error(f"Kite API error during modify_order: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during modify_order: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}")

# --- Run MCP Server ---
if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} MCP Server...")
    mcp.run()
