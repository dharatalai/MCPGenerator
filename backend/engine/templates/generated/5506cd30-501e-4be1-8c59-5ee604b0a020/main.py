from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import logging
import os
from dotenv import load_dotenv

# Import models and client
from models import (
    PlaceOrderParams, PlaceOrderResponse,
    ModifyOrderParams, ModifyOrderResponse,
    ErrorResponse,
    VarietyEnum, ExchangeEnum, TransactionTypeEnum, OrderTypeEnum, ProductEnum, ValidityEnum
)
from client import (
    ZerodhaKiteClient,
    KiteConnectAPIError, AuthenticationError, InputValidationError,
    OrderException, NetworkError, GeneralError
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialize MCP Server ---
mcp = FastMCP(
    service_name="ZerodhaKiteConnectOrders",
    description="Provides tools to manage trading orders (place, modify) using the Zerodha Kite Connect v3 API."
)

# --- Initialize API Client ---
# Client initialization requires environment variables ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN
try:
    kite_client = ZerodhaKiteClient()
except ValueError as e:
    logger.error(f"Failed to initialize ZerodhaKiteClient: {e}")
    # Optionally, exit or prevent server start if client init fails
    # raise SystemExit(f"Configuration Error: {e}")
    kite_client = None # Set to None to handle gracefully in tools

# --- Tool Definitions ---

@mcp.tool()
async def place_order(
    variety: VarietyEnum,
    tradingsymbol: str,
    exchange: ExchangeEnum,
    transaction_type: TransactionTypeEnum,
    order_type: OrderTypeEnum,
    quantity: int,
    product: ProductEnum,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity: ValidityEnum = ValidityEnum.DAY,
    validity_ttl: Optional[int] = None,
    iceberg_legs: Optional[int] = None,
    iceberg_quantity: Optional[int] = None,
    auction_number: Optional[str] = None,
    tag: Optional[str] = None
) -> Dict[str, Any]:
    """Places an order of a particular variety (regular, amo, co, iceberg, auction)."""
    if not kite_client:
        logger.error("place_order tool called but ZerodhaKiteClient is not initialized.")
        return ErrorResponse(status="error", message="Zerodha client not configured.").dict()

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
        logger.info(f"Executing place_order with params: {params.dict(exclude_none=True)}")
        result = await kite_client.place_order(params)
        logger.info(f"place_order successful: {result.dict()}")
        return result.dict()

    except (InputValidationError, OrderException, AuthenticationError, GeneralError, NetworkError) as e:
        logger.error(f"place_order failed: {type(e).__name__} - {e}")
        error_type = getattr(e, 'error_type', type(e).__name__)
        message = getattr(e, 'message', str(e))
        return ErrorResponse(status="error", message=message, error_type=error_type).dict()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in place_order: {e}")
        return ErrorResponse(status="error", message=f"An unexpected error occurred: {str(e)}", error_type="UnexpectedException").dict()

@mcp.tool()
async def modify_order(
    variety: VarietyEnum,
    order_id: str,
    parent_order_id: Optional[str] = None,
    order_type: Optional[OrderTypeEnum] = None,
    quantity: Optional[int] = None,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity: Optional[ValidityEnum] = None
) -> Dict[str, Any]:
    """Modifies attributes of a pending regular or CO order."""
    if not kite_client:
        logger.error("modify_order tool called but ZerodhaKiteClient is not initialized.")
        return ErrorResponse(status="error", message="Zerodha client not configured.").dict()

    # Basic validation for CO modification (only trigger_price allowed for CO)
    if variety == VarietyEnum.CO and any([order_type, quantity, price is not None, disclosed_quantity is not None, validity]):
         logger.warning(f"Attempting to modify fields other than trigger_price for a CO order (order_id: {order_id}). Only trigger_price is allowed.")
         # Note: The API might reject this anyway, but adding a check here can be helpful.
         # Consider raising an error or stripping disallowed fields depending on desired behavior.

    # Basic validation for regular order validity modification (must be DAY)
    if variety == VarietyEnum.REGULAR and validity and validity != ValidityEnum.DAY:
        logger.error(f"Invalid validity '{validity}' for modifying regular order {order_id}. Only 'DAY' is allowed.")
        return ErrorResponse(status="error", message="Invalid validity for modification. Only 'DAY' is allowed for regular orders.", error_type="InputValidationError").dict()

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
        logger.info(f"Executing modify_order for order_id {order_id} with params: {params.dict(exclude_none=True)}")
        result = await kite_client.modify_order(params)
        logger.info(f"modify_order successful for order_id {order_id}: {result.dict()}")
        return result.dict()

    except (InputValidationError, OrderException, AuthenticationError, GeneralError, NetworkError) as e:
        logger.error(f"modify_order failed for order_id {order_id}: {type(e).__name__} - {e}")
        error_type = getattr(e, 'error_type', type(e).__name__)
        message = getattr(e, 'message', str(e))
        return ErrorResponse(status="error", message=message, error_type=error_type).dict()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in modify_order for order_id {order_id}: {e}")
        return ErrorResponse(status="error", message=f"An unexpected error occurred: {str(e)}", error_type="UnexpectedException").dict()

# --- Graceful Shutdown ---
@mcp.on_event("shutdown")
async def shutdown_event():
    if kite_client:
        logger.info("Closing Zerodha Kite client...")
        await kite_client.close()
    logger.info("MCP server shutdown complete.")

# --- Run Server ---
if __name__ == "__main__":
    # Example: Run with uvicorn programmatically (optional)
    # import uvicorn
    # uvicorn.run(mcp, host="0.0.0.0", port=8000)

    # Standard way to run is via CLI: uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
    logger.info("Starting Zerodha Kite Connect Orders MCP Server.")
    logger.info("Run with: uvicorn main:mcp --host <host> --port <port> [--reload]")
    # The mcp.run() method is for development/testing, use Uvicorn for production.
    # mcp.run() # Uncomment for simple testing, but Uvicorn is preferred.
