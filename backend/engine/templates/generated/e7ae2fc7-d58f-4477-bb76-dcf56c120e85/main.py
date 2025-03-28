from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional
from pydantic import ValidationError
import logging
import asyncio
import os
from dotenv import load_dotenv

# Import models and client
from models import PlaceOrderParams, PlaceOrderResponse, ErrorResponse, VarietyType, ExchangeType, TransactionType, OrderType, ProductType, ValidityType
from client import KiteConnectClient, KiteConnectError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="zerodha_kite_connect_orders",
    description="MCP Server for managing orders (placing, modifying, cancelling, retrieving) and trades using the Zerodha Kite Connect API v3."
)

# Initialize Kite Connect Client
# Client initialization might raise ValueError if env vars are missing
try:
    kite_client = KiteConnectClient()
except ValueError as e:
    logger.error(f"Failed to initialize KiteConnectClient: {e}")
    # Optionally, exit or prevent server startup if client can't be initialized
    # raise SystemExit(f"Configuration error: {e}")
    kite_client = None # Set to None to handle gracefully in tool calls

@mcp.tool()
async def place_order(
    variety: VarietyType,
    tradingsymbol: str,
    exchange: ExchangeType,
    transaction_type: TransactionType,
    order_type: OrderType,
    quantity: int,
    product: ProductType,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None,
    validity: ValidityType = "DAY",
    validity_ttl: Optional[int] = None,
    iceberg_legs: Optional[int] = None,
    tag: Optional[str] = None
) -> Dict[str, Any]:
    """Place an order of a specific variety (regular, amo, co, iceberg, auction).
    
    Args:
        variety: Order variety (regular, amo, co, iceberg, auction).
        tradingsymbol: Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY21JUNFUT').
        exchange: Name of the exchange (NSE, BSE, NFO, CDS, BCD, MCX).
        transaction_type: Transaction type (BUY or SELL).
        order_type: Order type (MARKET, LIMIT, SL, SL-M).
        quantity: Quantity to transact (must be positive).
        product: Product type (CNC, NRML, MIS, MTF).
        price: The price for LIMIT or SL orders. Required for LIMIT/SL.
        trigger_price: The trigger price for SL, SL-M, or CO orders. Required for SL/SL-M.
        disclosed_quantity: Quantity to disclose publicly (equity only, non-negative).
        validity: Order validity (DAY, IOC, TTL). Defaults to DAY.
        validity_ttl: Order life span in minutes. Required if validity is TTL.
        iceberg_legs: Total number of legs for iceberg order (2-10). Required if variety is iceberg.
        tag: An optional tag for the order (Max 20 chars).

    Returns:
        A dictionary containing the order_id on success, or an error dictionary on failure.
    """
    if kite_client is None:
        logger.error("Kite client is not initialized. Cannot place order.")
        return ErrorResponse(status="error", message="Kite client not initialized due to configuration error.", error_type="ConfigurationError").dict()
        
    try:
        # Validate parameters using Pydantic model
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
            tag=tag
        )

        logger.info(f"Received place_order request for {tradingsymbol}, quantity {quantity}")
        
        # Call the client method
        response: PlaceOrderResponse = await kite_client.place_order(variety=variety, params=params)
        
        logger.info(f"Successfully placed order {response.order_id} for {tradingsymbol}")
        return response.dict()

    except ValidationError as e:
        logger.warning(f"Input validation failed for place_order: {e.errors()}")
        # Return a structured error based on Pydantic validation details
        return ErrorResponse(
            status="error", 
            message=f"Input validation failed: {e.errors()}", 
            error_type="ValidationError"
        ).dict()
        
    except KiteConnectError as e:
        logger.error(f"Kite API error during place_order: {e.message} (Type: {e.error_type})")
        return e.to_dict() # Use the error's built-in dict representation
        
    except Exception as e:
        logger.exception(f"Unexpected error in place_order tool: {str(e)}")
        return ErrorResponse(
            status="error", 
            message=f"An unexpected server error occurred: {str(e)}", 
            error_type="InternalServerError"
        ).dict()

# Add a health check endpoint (optional but good practice)
@mcp.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": mcp.service_name}

# Graceful shutdown
@mcp.on_event("shutdown")
async def shutdown_event():
    if kite_client:
        logger.info("Shutting down Kite client...")
        await kite_client.close()
    logger.info("MCP server shutdown complete.")

if __name__ == "__main__":
    # Run the MCP server using uvicorn
    # Use 'uvicorn main:mcp.app --reload' for development
    # Use 'uvicorn main:mcp.app --host 0.0.0.0 --port 8000' for production
    import uvicorn
    logger.info(f"Starting MCP server '{mcp.service_name}'...")
    # Note: Uvicorn should be run from the command line, this is illustrative
    # uvicorn.run(mcp.app, host="127.0.0.1", port=8000)
    print("MCP server defined. Run with: uvicorn main:mcp.app --reload")
