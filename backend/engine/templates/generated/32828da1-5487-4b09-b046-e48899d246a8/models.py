from pydantic import BaseModel, Field
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
    MCX = "MCX"
    BFO = "BFO"
    CDS = "CDS"
    BCD = "BCD"

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SLM = "SL-M"

class ProductType(str, Enum):
    CNC = "CNC"  # Cash & Carry for equity
    NRML = "NRML" # Normal for F&O, Currency, Commodity
    MIS = "MIS"  # Margin Intraday Squareoff
    BO = "BO"    # Bracket Order (deprecated/restricted)
    CO = "CO"    # Cover Order

class ValidityType(str, Enum):
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    TTL = "TTL"  # Time to Live (in minutes)

# --- Input Models --- 

class PlaceOrderInput(BaseModel):
    variety: OrderVariety = Field(..., description="The variety of the order (e.g., 'regular', 'co').")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'INFY', 'SBIN').")
    exchange: ExchangeType = Field(..., description="Name of the exchange (e.g., 'NSE', 'MCX').")
    transaction_type: TransactionType = Field(..., description="'BUY' or 'SELL'.")
    order_type: OrderType = Field(..., description="Order type (e.g., 'MARKET', 'LIMIT').")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product type (e.g., 'CNC', 'MIS').")
    validity: ValidityType = Field(default=ValidityType.DAY, description="Order validity ('DAY', 'IOC', 'TTL').")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M, CO orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10).")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs).")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction.")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag (alphanumeric, max 20 chars).")

class ModifyOrderInput(BaseModel):
    variety: OrderVariety = Field(..., description="The variety of the order being modified.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="Required for modifying second leg of CO.")
    order_type: Optional[OrderType] = Field(None, description="New order type.")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity.")
    price: Optional[float] = Field(None, description="New price.")
    trigger_price: Optional[float] = Field(None, description="New trigger price.")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity.")
    validity: Optional[ValidityType] = Field(None, description="New validity.")

class CancelOrderInput(BaseModel):
    variety: OrderVariety = Field(..., description="The variety of the order being cancelled.")
    order_id: str = Field(..., description="The ID of the order to cancel.")
    parent_order_id: Optional[str] = Field(None, description="Required for cancelling second leg of CO.")

class GetOrdersInput(BaseModel):
    # No input parameters needed for get_orders based on the plan
    pass 

# --- Output Models --- 

class PlaceOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID assigned by the exchange.")

class ModifyOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID of the modified order.")

class CancelOrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID of the cancelled order.")

# Define a model for individual order details returned by get_orders
# This is a simplified representation based on common fields in Kite API
class OrderDetails(BaseModel):
    order_id: str
    parent_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    status: str
    status_message: Optional[str] = None
    tradingsymbol: str
    exchange: ExchangeType
    transaction_type: TransactionType
    order_type: OrderType
    product: ProductType
    validity: ValidityType
    price: float
    quantity: int
    trigger_price: float
    average_price: float
    filled_quantity: int
    pending_quantity: int
    cancelled_quantity: int
    disclosed_quantity: int
    order_timestamp: str # Assuming timestamp is returned as string
    exchange_timestamp: Optional[str] = None
    variety: OrderVariety
    tag: Optional[str] = None
    # Add other fields as needed based on actual API response
    # meta: Optional[Dict[str, Any]] = None
    # auction_number: Optional[str] = None

# Model for representing errors from the Kite API
class KiteApiError(BaseModel):
    status: str = "error"
    error_type: str
    message: str
