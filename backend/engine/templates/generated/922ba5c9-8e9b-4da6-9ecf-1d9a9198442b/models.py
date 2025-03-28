from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

# --- Enums based on Kite Connect API documentation ---

class VarietyEnum(str, Enum):
    REGULAR = "regular"
    AMO = "amo"
    CO = "co"
    ICEBERG = "iceberg"
    AUCTION = "auction"

class ExchangeEnum(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    CDS = "CDS"
    BCD = "BCD"
    MCX = "MCX"

class TransactionTypeEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderTypeEnum(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class ProductEnum(str, Enum):
    CNC = "CNC"
    NRML = "NRML"
    MIS = "MIS"
    MTF = "MTF"

class ValidityEnum(str, Enum):
    DAY = "DAY"
    IOC = "IOC"
    TTL = "TTL"

# --- Input Parameter Models ---

class PlaceOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, amo, co, iceberg, auction). To be included in the URL path.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeEnum = Field(..., description="Name of the exchange (NSE, BSE, NFO, CDS, BCD, MCX).")
    transaction_type: TransactionTypeEnum = Field(..., description="BUY or SELL.")
    order_type: OrderTypeEnum = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M).")
    quantity: int = Field(..., description="Quantity to transact.")
    product: ProductEnum = Field(..., description="Product type (CNC, NRML, MIS, MTF).")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders).")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: Optional[ValidityEnum] = Field(ValidityEnum.DAY, description="Order validity (DAY, IOC, TTL). Defaults to DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required for iceberg variety.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order. Required for iceberg variety.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required for auction variety.")
    tag: Optional[str] = Field(None, description="An optional tag to apply to an order (alphanumeric, max 20 chars).")

class ModifyOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, co). To be included in the URL path.")
    order_id: str = Field(..., description="The ID of the order to modify. To be included in the URL path.")
    parent_order_id: Optional[str] = Field(None, description="Required for modifying second-leg CO orders.")
    order_type: Optional[OrderTypeEnum] = Field(None, description="New order type (only for regular orders).")
    quantity: Optional[int] = Field(None, description="New quantity (only for regular orders).")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, LIMIT CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only for regular equity orders).")
    validity: Optional[ValidityEnum] = Field(None, description="New validity (only for regular orders, DAY or IOC).")

class CancelOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, co, amo, iceberg, auction). To be included in the URL path.")
    order_id: str = Field(..., description="The ID of the order to cancel. To be included in the URL path.")
    parent_order_id: Optional[str] = Field(None, description="Required for cancelling second-leg CO orders.")

class GetOrdersParams(BaseModel):
    # No parameters needed for this endpoint according to the plan
    pass

class GetOrderHistoryParams(BaseModel):
    order_id: str = Field(..., description="The ID of the order to retrieve history for. To be included in the URL path.")

# --- Response Models (Simplified based on common Kite Connect structures) ---

class PlaceOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID.")

class ModifyOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID.")

class CancelOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID.")

class Order(BaseModel):
    order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    order_timestamp: Optional[str] = None
    exchange_timestamp: Optional[str] = None
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
    # Add other fields as needed based on actual API response

class OrderHistoryEntry(BaseModel):
    order_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    order_timestamp: Optional[str] = None # Assuming timestamp is part of history
    # Add other fields relevant to history (e.g., rejection reason, update timestamp)
    # This structure might need refinement based on the actual API response for order history
    # Often, the history endpoint returns a list of full Order objects representing states.
    # Let's assume it returns objects similar to the Order model for now.
    exchange_order_id: Optional[str] = None
    exchange_timestamp: Optional[str] = None
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
