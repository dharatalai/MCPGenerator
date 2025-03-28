from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

# --- Enums based on Zerodha Kite Connect API Documentation ---

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
    CNC = "CNC"  # Cash N Carry for equity
    NRML = "NRML" # Normal for F&O, Currency, Commodity
    MIS = "MIS"  # Margin Intraday Squareoff
    MTF = "MTF"  # Margin Trading Facility

class ValidityEnum(str, Enum):
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    TTL = "TTL"  # Time to Live (in minutes)

# --- Input Models for Tools ---

class PlaceOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, amo, co, iceberg, auction)")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY23JUL18000CE').")
    exchange: ExchangeEnum = Field(..., description="Name of the exchange (NSE, BSE, NFO, CDS, BCD, MCX).")
    transaction_type: TransactionTypeEnum = Field(..., description="Transaction type: BUY or SELL.")
    order_type: OrderTypeEnum = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M).")
    quantity: int = Field(..., description="Quantity to transact.")
    product: ProductEnum = Field(..., description="Product type (CNC, NRML, MIS, MTF).")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders).")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades). Defaults to 0.")
    validity: ValidityEnum = Field(ValidityEnum.DAY, description="Order validity (DAY, IOC, TTL). Defaults to DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes (required for TTL validity orders).")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required for variety='iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs). Required for variety='iceberg'.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required for variety='auction'.")
    tag: Optional[str] = Field(None, description="An optional tag (alphanumeric, max 20 chars) to identify the order.")

    class Config:
        use_enum_values = True # Serialize enums to their string values

class ModifyOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, co).")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID if modifying a second leg of a multi-legged order (like CO).")
    order_type: Optional[OrderTypeEnum] = Field(None, description="New order type (only applicable for regular variety).")
    quantity: Optional[int] = Field(None, description="New quantity (only applicable for regular variety).")
    price: Optional[float] = Field(None, description="New price (only applicable for regular or CO LIMIT variety).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (applicable for SL, SL-M, CO LIMIT orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only applicable for regular variety equity trades). Defaults to 0.")
    validity: Optional[ValidityEnum] = Field(None, description="New validity (only applicable for regular variety). Must be DAY.")

    class Config:
        use_enum_values = True # Serialize enums to their string values

# --- Response Models ---

class PlaceOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID.")

class ModifyOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID of the modified order.")

class ErrorResponse(BaseModel):
    status: str = Field("error", description="Status indicator.")
    message: str = Field(..., description="Detailed error message.")
    error_type: Optional[str] = Field(None, description="Specific Kite Connect error type (e.g., InputException, TokenException).")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details.")
