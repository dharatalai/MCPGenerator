from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum

# --- Enums based on Kite Connect API documentation ---

class OrderVariety(str, Enum):
    REGULAR = "regular"
    AMO = "amo"
    CO = "co"
    ICEBERG = "iceberg"
    AUCTION = "auction"

class ExchangeType(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    CDS = "CDS"
    BCD = "BCD"
    MCX = "MCX"

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class ProductType(str, Enum):
    CNC = "CNC"  # Cash & Carry for equity
    NRML = "NRML" # Normal for F&O, CDS, MCX
    MIS = "MIS"  # Margin Intraday Squareoff
    MTF = "MTF" # Margin Trading Facility

class OrderValidity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    TTL = "TTL"  # Time to Live (in minutes)

class OrderStatus(str, Enum):
    # Common statuses, might need expansion based on API details
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    MODIFY_PENDING = "MODIFY PENDING"
    # Add other potential statuses

# --- Input Models for Tools ---

class PlaceOrderParams(BaseModel):
    variety: OrderVariety = Field(..., description="Order variety (regular, amo, co, iceberg, auction)")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., INFY, NIFTY23JUL17500CE)")
    exchange: ExchangeType = Field(..., description="Name of the exchange (NSE, BSE, NFO, CDS, BCD, MCX)")
    transaction_type: TransactionType = Field(..., description="BUY or SELL")
    order_type: OrderType = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M)")
    quantity: int = Field(..., gt=0, description="Quantity to transact")
    product: ProductType = Field(..., description="Margin product to use (CNC, NRML, MIS, MTF)")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders)")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="Quantity to disclose publicly (for equity trades)")
    validity: OrderValidity = Field(..., description="Order validity (DAY, IOC, TTL)")
    validity_ttl: Optional[int] = Field(None, gt=0, description="Order life span in minutes for TTL validity orders")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order type (2-10)")
    iceberg_quantity: Optional[int] = Field(None, gt=0, description="Split quantity for each iceberg leg order (quantity/iceberg_legs)")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag to apply to an order (alphanumeric, max 20 chars)")

    @validator('price', always=True)
    def check_price_for_limit(cls, v, values):
        if values.get('order_type') == OrderType.LIMIT and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') == OrderType.MARKET and v is not None:
            # Kite API might ignore price for market orders, but good practice to disallow
            raise ValueError('Price should not be provided for MARKET orders')
        return v

    @validator('trigger_price', always=True)
    def check_trigger_price_for_sl(cls, v, values):
        if values.get('order_type') in [OrderType.SL, OrderType.SL_M] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        return v

    @validator('validity_ttl', always=True)
    def check_validity_ttl(cls, v, values):
        if values.get('validity') == OrderValidity.TTL and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if values.get('validity') != OrderValidity.TTL and v is not None:
            raise ValueError('validity_ttl should only be provided for TTL validity')
        return v

    @validator('iceberg_legs', 'iceberg_quantity', always=True)
    def check_iceberg_params(cls, v, values, field):
        is_iceberg = values.get('variety') == OrderVariety.ICEBERG
        if is_iceberg and field.name == 'iceberg_legs' and v is None:
            raise ValueError('iceberg_legs is required for iceberg orders')
        if is_iceberg and field.name == 'iceberg_quantity' and v is None:
             # Note: Kite API might calculate this automatically if not provided, but explicit is often better.
             # Check API docs if this is strictly required or can be derived.
             # raise ValueError('iceberg_quantity is required for iceberg orders')
             pass # Assuming API might derive if not provided
        if not is_iceberg and v is not None:
            raise ValueError(f'{field.name} should only be provided for iceberg orders')
        return v

class ModifyOrderParams(BaseModel):
    variety: OrderVariety = Field(..., description="Order variety (regular, co)") # Note: API docs say regular, co, amo, iceberg, auction can be modified
    order_id: str = Field(..., description="The ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="Parent order id for second leg CO order modification")
    order_type: Optional[OrderType] = Field(None, description="New order type (only applicable for regular variety - check API docs for others)")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (only applicable for regular variety - check API docs for others)")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders)")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="New disclosed quantity (only applicable for regular variety - check API docs for others)")
    validity: Optional[OrderValidity] = Field(None, description="New validity (only applicable for regular variety, DAY or IOC - check API docs for others)")

    @validator('validity')
    def check_validity_options(cls, v):
        if v not in [None, OrderValidity.DAY, OrderValidity.IOC]:
            # Based on implementation plan, but double-check API docs if TTL is allowed for modification
            raise ValueError('Validity for modification can only be DAY or IOC (or None)')
        return v

class CancelOrderParams(BaseModel):
    variety: OrderVariety = Field(..., description="Order variety (regular, amo, co, iceberg, auction)")
    order_id: str = Field(..., description="The ID of the order to cancel")
    parent_order_id: Optional[str] = Field(None, description="Parent order id for second leg CO order cancellation")

class GetOrdersParams(BaseModel):
    # No parameters needed for fetching all orders for the day as per plan
    pass

# --- Return Models ---

class OrderIDResponse(BaseModel):
    order_id: str = Field(..., description="The unique ID of the order.")

class Order(BaseModel):
    # Based on common fields in Kite Connect orderbook response
    # Adjust fields based on actual API response structure
    order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    status: Optional[str] = None # Consider using OrderStatus enum if comprehensive
    status_message: Optional[str] = None
    status_message_raw: Optional[str] = None
    order_timestamp: Optional[str] = None # Consider datetime type
    exchange_timestamp: Optional[str] = None # Consider datetime type
    variety: Optional[str] = None # Consider OrderVariety enum
    exchange: Optional[str] = None # Consider ExchangeType enum
    tradingsymbol: Optional[str] = None
    instrument_token: Optional[int] = None
    order_type: Optional[str] = None # Consider OrderType enum
    transaction_type: Optional[str] = None # Consider TransactionType enum
    validity: Optional[str] = None # Consider OrderValidity enum
    product: Optional[str] = None # Consider ProductType enum
    quantity: Optional[int] = None
    disclosed_quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    average_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    pending_quantity: Optional[int] = None
    cancelled_quantity: Optional[int] = None
    tag: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    # Add any other relevant fields from the API response

class KiteErrorResponse(BaseModel):
    error_type: str = Field(..., description="Category of the error.")
    message: str = Field(..., description="Detailed error message.")
    status_code: Optional[int] = Field(None, description="HTTP status code associated with the error.")
