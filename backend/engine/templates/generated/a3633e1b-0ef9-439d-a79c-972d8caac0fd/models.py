from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator

# --- Enums based on Kite Connect API documentation ---

class Variety(str, Enum):
    REGULAR = "regular"
    AMO = "amo"
    CO = "co"
    ICEBERG = "iceberg"
    AUCTION = "auction"

class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    CDS = "CDS"
    MCX = "MCX"
    BCD = "BCD"
    BFO = "BFO"

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class Product(str, Enum):
    CNC = "CNC"  # Cash & Carry for equity
    NRML = "NRML" # Normal for F&O, currency, commodity
    MIS = "MIS"  # Margin Intraday Squareoff
    MTF = "MTF"  # Margin Trading Facility

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"    # Stoploss limit
    SLM = "SL-M" # Stoploss market

class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    TTL = "TTL"  # Time to Live

# --- Input Models for MCP Tools ---

class PlaceOrderParams(BaseModel):
    variety: Variety = Field(..., description="Order variety (regular, amo, co, iceberg, auction).")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., INFY, NIFTY23JULIFUT).")
    exchange: Exchange = Field(..., description="Name of the exchange (e.g., NSE, NFO, BSE)." )
    transaction_type: TransactionType = Field(..., description="Transaction type: BUY or SELL.")
    quantity: int = Field(..., description="Quantity to transact.", gt=0)
    product: Product = Field(..., description="Product type (CNC, NRML, MIS, MTF).")
    order_type: OrderType = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M).")
    price: Optional[float] = Field(None, description="The price for LIMIT orders. Required if order_type is LIMIT or SL.", ge=0)
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders. Required if order_type is SL or SL-M.", ge=0)
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).", ge=0)
    validity: Optional[Validity] = Field(Validity.DAY, description="Order validity (DAY, IOC, TTL). Default is DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders (1 to 1440). Required if validity is TTL.", ge=1, le=1440)
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required for variety='iceberg'.", ge=2, le=10)
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs). Required for variety='iceberg'.", ge=1)
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required for variety='auction'.")
    tag: Optional[str] = Field(None, description="An optional tag (alphanumeric, max 20 chars) to identify the order.", max_length=20)

    @validator('price', always=True)
    def check_price(cls, v, values):
        order_type = values.get('order_type')
        if order_type in [OrderType.LIMIT, OrderType.SL] and v is None:
            raise ValueError('Price is required for LIMIT and SL order types')
        if order_type not in [OrderType.LIMIT, OrderType.SL] and v is not None:
             # Kite Connect API might ignore it, but better to be explicit
             pass # Allow setting price even if not strictly needed, API might handle it
        return v

    @validator('trigger_price', always=True)
    def check_trigger_price(cls, v, values):
        order_type = values.get('order_type')
        if order_type in [OrderType.SL, OrderType.SLM] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M order types')
        if order_type not in [OrderType.SL, OrderType.SLM] and v is not None:
            # Kite Connect API might ignore it
            pass # Allow setting trigger_price even if not strictly needed
        return v

    @validator('validity_ttl', always=True)
    def check_validity_ttl(cls, v, values):
        validity = values.get('validity')
        if validity == Validity.TTL and v is None:
            raise ValueError('validity_ttl is required when validity is TTL')
        if validity != Validity.TTL and v is not None:
            raise ValueError('validity_ttl is only applicable when validity is TTL')
        return v

    @validator('iceberg_legs', always=True)
    def check_iceberg_legs(cls, v, values):
        variety = values.get('variety')
        if variety == Variety.ICEBERG and v is None:
            raise ValueError('iceberg_legs is required when variety is iceberg')
        if variety != Variety.ICEBERG and v is not None:
            raise ValueError('iceberg_legs is only applicable when variety is iceberg')
        return v

    @validator('iceberg_quantity', always=True)
    def check_iceberg_quantity(cls, v, values):
        variety = values.get('variety')
        quantity = values.get('quantity')
        iceberg_legs = values.get('iceberg_legs')

        if variety == Variety.ICEBERG:
            if v is None:
                raise ValueError('iceberg_quantity is required when variety is iceberg')
            if quantity is not None and iceberg_legs is not None and v * iceberg_legs != quantity:
                 # Zerodha docs imply it should be quantity/legs, but API might just need quantity > iceberg_quantity
                 # Let's enforce the stricter check for clarity, can be relaxed if needed.
                 # raise ValueError('iceberg_quantity * iceberg_legs must equal total quantity')
                 # Relaxed check: ensure iceberg_quantity is less than total quantity
                 if v >= quantity:
                     raise ValueError('iceberg_quantity must be less than the total quantity')
            if quantity is not None and v is not None and quantity < v:
                 raise ValueError('iceberg_quantity cannot be greater than total quantity')

        if variety != Variety.ICEBERG and v is not None:
            raise ValueError('iceberg_quantity is only applicable when variety is iceberg')
        return v

    @validator('auction_number', always=True)
    def check_auction_number(cls, v, values):
        variety = values.get('variety')
        if variety == Variety.AUCTION and v is None:
            raise ValueError('auction_number is required when variety is auction')
        if variety != Variety.AUCTION and v is not None:
            raise ValueError('auction_number is only applicable when variety is auction')
        return v

class ModifyOrderParams(BaseModel):
    variety: Variety = Field(..., description="Order variety (typically regular or co). Check API docs for others.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID if modifying a second leg of a CO.")
    quantity: Optional[int] = Field(None, description="New quantity (for regular orders).", gt=0)
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).", ge=0)
    order_type: Optional[OrderType] = Field(None, description="New order type (only for regular orders, e.g., LIMIT, SL). Cannot change to/from MARKET.")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders).", ge=0)
    validity: Optional[Validity] = Field(None, description="New validity (only for regular orders, DAY or IOC). Cannot change to TTL.")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (for regular equity orders).", ge=0)

    @validator('validity')
    def check_validity(cls, v):
        if v == Validity.TTL:
            raise ValueError("Cannot modify validity to TTL")
        return v

    @validator('order_type')
    def check_order_type(cls, v):
        if v == OrderType.MARKET:
             # Generally cannot modify TO market, or FROM market if already placed
             # Let API handle specific rejection, but flag potential issue
             pass
        return v

class CancelOrderParams(BaseModel):
    variety: Variety = Field(..., description="Order variety (regular, co, amo, iceberg, auction).")
    order_id: str = Field(..., description="The ID of the order to cancel.")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID if cancelling a second leg of a CO.")

# --- Return Models (Optional, can use Dict directly) ---

class OrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID.")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Description of the error.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details, if available.")
