from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal, Dict, Any, Union
import datetime

# Define Literal types for allowed values based on Kite Connect API v3
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']
ModifyVarietyType = Literal['regular', 'co']
ModifyOrderType = Optional[OrderType]
ModifyValidityType = Optional[ValidityType]

class PlaceOrderParams(BaseModel):
    """Input model for placing an order."""
    variety: VarietyType = Field(..., description="The variety of the order.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="BUY or SELL.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product code.")
    price: Optional[float] = Field(None, description="The price to execute the order at (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (SL, SL-M). Required for SL/SL-M orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders. Required if validity is TTL.")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order type (2-10). Required if variety is iceberg.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order. Required if variety is iceberg.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required if variety is auction.")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag (alphanumeric, max 20 chars).")

    @validator('price')
    def price_required_for_limit(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('price is required for LIMIT orders')
        if values.get('order_type') != 'LIMIT' and v is not None:
             # Kite API might ignore it, but better to warn or raise
             # raise ValueError('price is only applicable for LIMIT orders')
             pass # Allow sending it, API might handle it
        return v

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        if values.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('trigger_price is required for SL and SL-M orders')
        if values.get('order_type') not in ['SL', 'SL-M'] and v is not None:
            # raise ValueError('trigger_price is only applicable for SL and SL-M orders')
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
        return v

    @validator('auction_number')
    def auction_number_required(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction variety')
        if values.get('variety') != 'auction' and v is not None:
            raise ValueError('auction_number is only applicable for auction variety')
        return v

class ModifyOrderParams(BaseModel):
    """Input model for modifying an order."""
    variety: ModifyVarietyType = Field(..., description="The variety of the order to modify ('regular' or 'co').")
    order_id: str = Field(..., description="The ID of the order to modify.")
    order_type: ModifyOrderType = Field(None, description="New order type (only for regular variety).")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (only for regular variety).")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, LIMIT CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only for regular variety).")
    validity: ModifyValidityType = Field(None, description="New validity (only for regular variety).")

    @validator('order_type', 'quantity', 'disclosed_quantity', 'validity')
    def regular_only_fields(cls, v, values, field):
        if values.get('variety') == 'co' and v is not None:
            raise ValueError(f"{field.name} cannot be modified for 'co' variety orders.")
        return v

    @validator('price')
    def price_check(cls, v, values):
        if values.get('variety') == 'co' and v is not None:
            raise ValueError("price cannot be modified for 'co' variety orders.")
        # Add check if order_type is changing to/from LIMIT if needed
        return v

    @validator('trigger_price')
    def trigger_price_check(cls, v, values):
        # Trigger price can be modified for regular SL/SL-M and CO limit orders
        # Add more specific validation based on target order_type if necessary
        return v

class CancelOrderParams(BaseModel):
    """Input model for cancelling an order."""
    variety: VarietyType = Field(..., description="The variety of the order to cancel.")
    order_id: str = Field(..., description="The ID of the order to cancel.")
    parent_order_id: Optional[str] = Field(None, description="Conditional parent order id for CO second leg cancellation.")

    @validator('parent_order_id')
    def parent_order_id_for_co(cls, v, values):
        # This might be needed if cancelling the second leg of a CO requires the parent_order_id
        # The Kite documentation isn't explicit on this for DELETE, but it's good practice to include if applicable.
        # if values.get('variety') == 'co' and v is None: # Check specific conditions if needed
        #     raise ValueError("parent_order_id might be required for cancelling CO legs")
        if values.get('variety') != 'co' and v is not None:
            raise ValueError("parent_order_id is only applicable for 'co' variety")
        return v

class GetOrderHistoryParams(BaseModel):
    """Input model for getting order history."""
    order_id: str = Field(..., description="The ID of the order to retrieve history for.")

class KiteResponse(BaseModel):
    """Generic response model for simple Kite API returns."""
    order_id: str

# Basic Order model based on typical fields in Kite Connect order book/history
# This might need adjustments based on the exact fields returned by the API
class Order(BaseModel):
    """Represents a single order object returned by Kite API."""
    order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    status_message_raw: Optional[str] = None
    order_timestamp: Optional[Union[datetime.datetime, str]] = None # Kite often returns strings
    exchange_timestamp: Optional[Union[datetime.datetime, str]] = None
    variety: Optional[str] = None
    exchange: Optional[str] = None
    tradingsymbol: Optional[str] = None
    instrument_token: Optional[int] = None
    order_type: Optional[str] = None
    transaction_type: Optional[str] = None
    validity: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[int] = None
    disclosed_quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    average_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    pending_quantity: Optional[int] = None
    cancelled_quantity: Optional[int] = None
    guid: Optional[str] = None
    market_protection: Optional[float] = None
    tag: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    # Allow extra fields as Kite API might add new ones
    class Config:
        extra = 'allow'
