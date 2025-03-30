from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict, Any

# Define Literal types for restricted parameter values
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']
ModifyVarietyType = Literal['regular', 'co']

class PlaceOrderParams(BaseModel):
    """Input model for placing an order."""
    variety: VarietyType = Field(..., description="The variety of the order.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY23JUL18500CE').")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product type (CNC, NRML, MIS, MTF).")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders).")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes (required for TTL validity orders).")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order type (2-10). Required for variety='iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs). Required for variety='iceberg'.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required for variety='auction'.")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag to apply to an order (alphanumeric, max 20 chars).")

    @validator('price')
    def check_price(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') == 'MARKET' and v is not None:
            # Kite API might ignore price for MARKET, but good practice to not send it
            pass # Or raise ValueError('Price should not be provided for MARKET orders')
        return v

    @validator('trigger_price')
    def check_trigger_price(cls, v, values):
        if values.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        return v

    @validator('validity_ttl')
    def check_validity_ttl(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        return v

    @validator('iceberg_legs')
    def check_iceberg_legs(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_legs is required for iceberg variety')
        return v

    @validator('iceberg_quantity')
    def check_iceberg_quantity(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_quantity is required for iceberg variety')
        # Add check: iceberg_quantity * iceberg_legs should ideally equal quantity
        # This logic might be complex depending on rounding, leave to API validation for now
        return v

    @validator('auction_number')
    def check_auction_number(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction variety')
        return v

class ModifyOrderParams(BaseModel):
    """Input model for modifying an order."""
    variety: ModifyVarietyType = Field(..., description="The variety of the order to modify. Currently supports 'regular' and 'co'.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="Parent order id is required for second leg CO modification.")
    # Fields applicable primarily for 'regular' variety modification
    order_type: Optional[OrderType] = Field(None, description="New order type (only applicable for variety='regular').")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (only applicable for variety='regular').")
    # Price/Trigger Price applicable for both regular (LIMIT/SL/SL-M) and CO
    price: Optional[float] = Field(None, description="New price (applicable for LIMIT orders for variety='regular', or for CO orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (applicable for SL, SL-M orders for variety='regular', or for LIMIT CO orders).")
    # Fields applicable only for 'regular' variety modification
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only applicable for variety='regular').")
    validity: Optional[ValidityType] = Field(None, description="New validity (only applicable for variety='regular').")

    @validator('parent_order_id')
    def check_parent_order_id(cls, v, values):
        # Basic check, actual requirement depends on whether it's a second leg CO order
        # This might need more context from the order being modified
        return v

class CancelOrderParams(BaseModel):
    """Input model for cancelling an order."""
    variety: VarietyType = Field(..., description="The variety of the order to cancel.")
    order_id: str = Field(..., description="The ID of the order to cancel.")
    parent_order_id: Optional[str] = Field(None, description="Parent order id is required for second leg CO cancellation.")

class OrderResponse(BaseModel):
    """Standard response model for successful order operations."""
    order_id: str = Field(..., description="The unique order ID.")
    # Kite API might return more data, but order_id is the key identifier

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Description of the error.")
    type: str = Field(..., description="Type of the error (e.g., KiteInputException, ServerError).")
