from pydantic import BaseModel, Field
from typing import Optional, Dict
from enum import Enum

# --- Enums based on Kite Connect API --- #

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
    MCX = "MCX"
    CDS = "CDS"
    BFO = "BFO"
    BCD = "BCD"

class TransactionTypeEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderTypeEnum(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SLM = "SL-M"

class ProductEnum(str, Enum):
    CNC = "CNC"
    NRML = "NRML"
    MIS = "MIS"
    MTF = "MTF"

class ValidityEnum(str, Enum):
    DAY = "DAY"
    IOC = "IOC"
    TTL = "TTL"

# --- Input Models for Tools --- #

class PlaceOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety ('regular', 'amo', 'co', 'iceberg', 'auction')")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'SBIN')")
    exchange: ExchangeEnum = Field(..., description="Name of the exchange (e.g., 'NSE', 'BSE', 'NFO')")
    transaction_type: TransactionTypeEnum = Field(..., description="Transaction type ('BUY' or 'SELL')")
    order_type: OrderTypeEnum = Field(..., description="Order type ('MARKET', 'LIMIT', 'SL', 'SL-M')")
    quantity: int = Field(..., description="Quantity to transact")
    product: ProductEnum = Field(..., description="Product type ('CNC', 'NRML', 'MIS', 'MTF')")
    price: Optional[float] = Field(None, description="The price for LIMIT orders")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades)")
    validity: ValidityEnum = Field(..., description="Order validity ('DAY', 'IOC', 'TTL')")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10)")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs)")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction")
    tag: Optional[str] = Field(None, description="Optional tag for the order (alphanumeric, max 20 chars)")

class ModifyOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety ('regular', 'co', etc.)")
    order_id: str = Field(..., description="The ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID if modifying a second-leg CO order (usually not needed for standard modification)")
    order_type: Optional[OrderTypeEnum] = Field(None, description="New order type (Regular orders only)")
    quantity: Optional[int] = Field(None, description="New quantity (Regular orders only)")
    price: Optional[float] = Field(None, description="New price (Regular LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="New trigger price (Regular SL/SL-M or CO orders)")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (Regular equity orders only)")
    validity: Optional[ValidityEnum] = Field(None, description="New validity (Regular orders only, typically DAY or IOC)")

# --- Output/Response Models --- #

class OrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID.")

class ErrorResponse(BaseModel):
    status: str = Field("error", description="Indicates an error occurred.")
    message: str = Field(..., description="Description of the error.")
    error_type: Optional[str] = Field(None, description="Category of the error (e.g., InputException, TokenException).")
    data: Optional[Dict] = Field(None, description="Additional error data, if available.")
