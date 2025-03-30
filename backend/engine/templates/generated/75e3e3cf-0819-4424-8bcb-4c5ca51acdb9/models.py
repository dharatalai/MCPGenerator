from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

# --- Enums for specific fields (optional but recommended for validation) ---

class VarietyEnum(str, Enum):
    regular = "regular"
    amo = "amo"
    co = "co"
    iceberg = "iceberg"
    auction = "auction"

class TransactionTypeEnum(str, Enum):
    buy = "BUY"
    sell = "SELL"

class OrderTypeEnum(str, Enum):
    market = "MARKET"
    limit = "LIMIT"
    sl = "SL"
    slm = "SL-M"

class ProductEnum(str, Enum):
    cnc = "CNC"
    nrml = "NRML"
    mis = "MIS"
    mtf = "MTF"

class ValidityEnum(str, Enum):
    day = "DAY"
    ioc = "IOC"
    ttl = "TTL"

# --- Input Parameter Models ---

class PlaceOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument")
    exchange: str = Field(..., description="Name of the exchange (e.g., NSE, BSE, NFO, MCX)")
    transaction_type: TransactionTypeEnum = Field(..., description="BUY or SELL")
    order_type: OrderTypeEnum = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M)")
    quantity: int = Field(..., gt=0, description="Quantity to transact")
    product: ProductEnum = Field(..., description="Product code (CNC, NRML, MIS, MTF)")
    price: Optional[float] = Field(None, description="The price for LIMIT orders")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity)")
    validity: Optional[ValidityEnum] = Field(ValidityEnum.day, description="Order validity (DAY, IOC, TTL). Default is DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order (2-10)")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order")
    auction_number: Optional[str] = Field(None, description="Unique identifier for a particular auction")
    tag: Optional[str] = Field(None, max_length=20, description="Optional tag for the order (alphanumeric, max 20 chars)")

    # TODO: Add custom validation logic if needed (e.g., price required for LIMIT)

class ModifyOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, co)")
    order_id: str = Field(..., description="ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="Parent order ID if modifying a second leg CO order")
    order_type: Optional[OrderTypeEnum] = Field(None, description="New order type (only for regular orders)")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (only for regular orders)")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders)")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only for regular equity orders)")
    validity: Optional[ValidityEnum] = Field(None, description="New validity (only for regular orders, DAY or IOC)")

class CancelOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, amo, co, iceberg, auction)")
    order_id: str = Field(..., description="ID of the order to cancel")
    parent_order_id: Optional[str] = Field(None, description="Parent order ID if cancelling a second leg CO order")

class GetOrderHistoryParams(BaseModel):
    order_id: str = Field(..., description="ID of the order to retrieve history for")

# --- Response Models (Placeholders - Define based on actual Kite API response structure) ---

class OrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID")

class OrderDetails(BaseModel):
    # Example fields - adjust based on Kite API v3 documentation
    order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    status_message_raw: Optional[str] = None
    order_timestamp: Optional[str] = None # Consider datetime type
    exchange_timestamp: Optional[str] = None # Consider datetime type
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
    tag: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class OrderHistoryItem(BaseModel):
    # Example fields - adjust based on Kite API v3 documentation for order history
    order_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    order_timestamp: Optional[str] = None # Consider datetime type
    # Add other relevant fields from the history/update structure
    # Example: quantity, price, trigger_price changes if applicable

# --- Error Response Model ---

class ErrorResponse(BaseModel):
    error: str
    error_type: Optional[str] = None
    status_code: Optional[int] = None
