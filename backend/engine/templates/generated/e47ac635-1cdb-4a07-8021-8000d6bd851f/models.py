from pydantic import BaseModel, Field, validator
from typing import Optional, Dict
from typing_extensions import Literal

# Define Literal types for parameters
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: VarietyType = Field(..., description="Order variety type.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product code.")
    price: Optional[float] = Field(None, description="The price to execute the order at (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (SL, SL-M).")
    disclosed_quantity: Optional[int] = Field(None, gt=0, description="Quantity to disclose publicly (for equity trades).")
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, gt=0, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order type (2-10). Required if variety is 'iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, gt=0, description="Split quantity for each iceberg leg order. Required if variety is 'iceberg'.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required if variety is 'auction'.")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag to apply to an order (alphanumeric, max 20 chars).")

    @validator('price')
    def price_required_for_limit(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') != 'LIMIT' and v is not None:
             # Kite API might ignore it, but better to be explicit or raise error
             # raise ValueError('Price is only applicable for LIMIT orders')
             pass # Allow sending it, API might handle it
        return v

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        if values.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('Trigger price is required for SL/SL-M orders')
        if values.get('order_type') not in ['SL', 'SL-M'] and v is not None:
            # raise ValueError('Trigger price is only applicable for SL/SL-M orders')
            pass # Allow sending it
        return v

    @validator('validity_ttl')
    def validity_ttl_required(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if values.get('validity') != 'TTL' and v is not None:
            raise ValueError('validity_ttl is only applicable for TTL validity')
        return v

    @validator('iceberg_legs')
    def iceberg_legs_required(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_legs is required for iceberg variety')
        if values.get('variety') != 'iceberg' and v is not None:
            raise ValueError('iceberg_legs is only applicable for iceberg variety')
        return v

    @validator('iceberg_quantity')
    def iceberg_quantity_required(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_quantity is required for iceberg variety')
        if values.get('variety') != 'iceberg' and v is not None:
            raise ValueError('iceberg_quantity is only applicable for iceberg variety')
        # Add validation: iceberg_quantity should be less than total quantity
        if v is not None and values.get('quantity') is not None and v >= values['quantity']:
             raise ValueError('iceberg_quantity must be less than total quantity')
        return v

    @validator('auction_number')
    def auction_number_required(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction variety')
        if values.get('variety') != 'auction' and v is not None:
            raise ValueError('auction_number is only applicable for auction variety')
        return v

class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order."""
    variety: VarietyType = Field(..., description="Order variety type.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    order_type: Optional[OrderType] = Field(None, description="New order type.")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity.")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M orders).")
    disclosed_quantity: Optional[int] = Field(None, gt=0, description="New disclosed quantity.")
    validity: Optional[ValidityType] = Field(None, description="New validity.")

    @validator('price')
    def price_check_for_limit(cls, v, values):
        # Price is only relevant if changing to or modifying a LIMIT order
        # Actual validation depends on the original order and the new order_type if provided
        # Keeping it simple here, Kite API will perform the final validation
        return v

    @validator('trigger_price')
    def trigger_price_check_for_sl(cls, v, values):
        # Trigger price is only relevant if changing to or modifying an SL/SL-M order
        return v

class OrderResponse(BaseModel):
    """Standard success response containing the order ID."""
    order_id: str = Field(..., description="The unique identifier for the order.")

class ErrorResponse(BaseModel):
    """Standard error response."""
    error_type: str = Field(..., description="Type of error.")
    message: str = Field(..., description="Detailed error message.")
    code: int = Field(..., description="HTTP status code or custom error code.")
