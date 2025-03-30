from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, validator
import datetime

# Define Literal types for parameters
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']
ModifyVarietyType = Literal['regular', 'co', 'amo', 'iceberg']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: VarietyType = Field(..., description="Order variety.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product code.")
    price: Optional[float] = Field(None, description="The price to execute the order at (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (SL, SL-M, CO).")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order type (2-10).")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction.")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag to apply to an order (alphanumeric, max 20 chars).")

    @validator('price')
    def check_price_for_limit(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') == 'MARKET' and v is not None:
            # Kite API might ignore it, but good practice to validate
            # raise ValueError('Price should not be set for MARKET orders')
            pass # Allow sending 0 for market orders if API requires
        return v

    @validator('trigger_price')
    def check_trigger_price(cls, v, values):
        if values.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        if values.get('variety') == 'co' and v is None:
             raise ValueError('Trigger price is required for CO orders')
        return v

    @validator('validity_ttl')
    def check_validity_ttl(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if values.get('validity') != 'TTL' and v is not None:
            raise ValueError('validity_ttl is only applicable for TTL validity')
        return v

    @validator('iceberg_legs', 'iceberg_quantity')
    def check_iceberg_params(cls, v, values, field):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError(f'{field.name} is required for iceberg orders')
        if values.get('variety') != 'iceberg' and v is not None:
            raise ValueError(f'{field.name} is only applicable for iceberg orders')
        # Additional validation: iceberg_quantity should be less than total quantity
        if field.name == 'iceberg_quantity' and v is not None and values.get('quantity') is not None:
            if v >= values['quantity']:
                 raise ValueError('iceberg_quantity must be less than total quantity')
            if values.get('iceberg_legs') is not None and values['quantity'] / v > values['iceberg_legs']:
                 # This logic might need refinement based on exact Kite rules
                 pass
        return v

    @validator('auction_number')
    def check_auction_number(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction orders')
        if values.get('variety') != 'auction' and v is not None:
            raise ValueError('auction_number is only applicable for auction orders')
        return v


class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order."""
    variety: ModifyVarietyType = Field(..., description="Order variety.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="Required for modifying second leg of CO.")
    order_type: Optional[OrderType] = Field(None, description="New order type (regular orders).")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (regular orders).")
    price: Optional[float] = Field(None, description="New price (LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (SL, SL-M, CO).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (regular equity orders).")
    validity: Optional[ValidityType] = Field(None, description="New validity (regular orders).")

    @validator('parent_order_id')
    def check_parent_order_id_for_co(cls, v, values):
        # This validation might depend on which leg is being modified, API specifics needed.
        # Assuming modification applies to the main order unless parent_order_id is specified for the second leg.
        # if values.get('variety') == 'co' and v is None: # This might be too strict
        #     raise ValueError('parent_order_id might be required for modifying CO legs')
        return v

class CancelOrderParams(BaseModel):
    """Parameters for cancelling an order."""
    variety: VarietyType = Field(..., description="Order variety.")
    order_id: str = Field(..., description="The ID of the order to cancel.")
    parent_order_id: Optional[str] = Field(None, description="Required for cancelling second leg of CO.")

    @validator('parent_order_id')
    def check_parent_order_id_for_co_cancel(cls, v, values):
        # Similar to modify, API specifics needed for when parent_order_id is strictly required.
        # if values.get('variety') == 'co' and v is None: # Might be too strict
        #     raise ValueError('parent_order_id might be required for cancelling CO legs')
        return v

class GetOrdersParams(BaseModel):
    """Parameters for retrieving orders (currently none)."""
    pass # No parameters needed for fetching all orders for the day

class OrderIDResponse(BaseModel):
    """Standard response containing an order ID."""
    order_id: str = Field(..., description="The ID of the order affected by the operation.")

class Order(BaseModel):
    """Represents a single order retrieved from the API."""
    # Based on common fields in Kite Connect order responses
    order_id: str
    parent_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    status: str # e.g., OPEN, COMPLETE, CANCELLED, REJECTED
    status_message: Optional[str] = None
    status_message_raw: Optional[str] = None
    order_timestamp: datetime.datetime
    exchange_timestamp: Optional[datetime.datetime] = None
    variety: str
    exchange: str
    tradingsymbol: str
    instrument_token: int
    order_type: str
    transaction_type: str
    validity: str
    validity_ttl: Optional[int] = None # Added based on PlaceOrderParams
    product: str
    quantity: int
    disclosed_quantity: int
    price: float
    trigger_price: float
    average_price: float
    filled_quantity: int
    pending_quantity: int
    cancelled_quantity: int # Added for clarity
    market_protection: Optional[float] = Field(None, alias="market_protection") # Check alias if needed
    meta: Optional[Dict[str, Any]] = None
    tag: Optional[str] = None
    guid: Optional[str] = None # Internal ID

    class Config:
        allow_population_by_field_name = True # If API uses snake_case
