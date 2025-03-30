from pydantic import BaseModel, Field, validator
from typing import Optional, Dict
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

# --- Input Models for Tools --- 

class PlaceOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, amo, co, iceberg, auction)")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., INFY, NIFTY23JUL)")
    exchange: ExchangeEnum = Field(..., description="Name of the exchange (e.g., NSE, BSE, NFO)")
    transaction_type: TransactionTypeEnum = Field(..., description="BUY or SELL")
    order_type: OrderTypeEnum = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M)")
    quantity: int = Field(..., description="Quantity to transact", gt=0)
    product: ProductEnum = Field(..., description="Product type (CNC, NRML, MIS, MTF)")
    validity: ValidityEnum = Field(..., description="Order validity (DAY, IOC, TTL)")
    price: Optional[float] = Field(None, description="The price for LIMIT orders", ge=0)
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders", ge=0)
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity)", ge=0)
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders (1 to 1440)", ge=1, le=1440)
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order (2-10)", ge=2, le=10)
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg (must be >= 1)", ge=1)
    auction_number: Optional[str] = Field(None, description="Unique identifier for a specific auction")
    tag: Optional[str] = Field(None, description="Optional tag for the order (alphanumeric, max 20 chars)", max_length=20)

    @validator('price')
    def price_required_for_limit(cls, v, values):
        if values.get('order_type') == OrderTypeEnum.LIMIT and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') != OrderTypeEnum.LIMIT and v is not None:
            # Kite might ignore it, but better to be explicit
            # raise ValueError('Price should only be provided for LIMIT orders')
            pass # Allow price for other types if API ignores it
        return v

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        if values.get('order_type') in [OrderTypeEnum.SL, OrderTypeEnum.SLM] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        if values.get('order_type') not in [OrderTypeEnum.SL, OrderTypeEnum.SLM] and v is not None:
            # raise ValueError('Trigger price should only be provided for SL and SL-M orders')
            pass # Allow trigger_price for other types if API ignores it
        return v

    @validator('validity_ttl')
    def validity_ttl_required_for_ttl(cls, v, values):
        if values.get('validity') == ValidityEnum.TTL and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if values.get('validity') != ValidityEnum.TTL and v is not None:
            raise ValueError('validity_ttl should only be provided for TTL validity')
        return v

    @validator('iceberg_legs', 'iceberg_quantity')
    def iceberg_params_for_iceberg_variety(cls, v, field, values):
        if values.get('variety') == VarietyEnum.ICEBERG and v is None:
            raise ValueError(f'{field.name} is required for iceberg variety')
        if values.get('variety') != VarietyEnum.ICEBERG and v is not None:
            raise ValueError(f'{field.name} should only be provided for iceberg variety')
        return v

    @validator('auction_number')
    def auction_number_for_auction_variety(cls, v, values):
        if values.get('variety') == VarietyEnum.AUCTION and v is None:
            raise ValueError('auction_number is required for auction variety')
        if values.get('variety') != VarietyEnum.AUCTION and v is not None:
            raise ValueError('auction_number should only be provided for auction variety')
        return v

class ModifyOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, co)") # Note: AMO, Iceberg, Auction cannot be modified via API
    order_id: str = Field(..., description="The ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="Parent order ID if modifying a second-leg CO order")
    order_type: Optional[OrderTypeEnum] = Field(None, description="New order type (Regular orders only)")
    quantity: Optional[int] = Field(None, description="New quantity (Regular orders only)", gt=0)
    price: Optional[float] = Field(None, description="New price (LIMIT orders)", ge=0)
    trigger_price: Optional[float] = Field(None, description="New trigger price (SL, SL-M, CO orders)", ge=0)
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (Regular orders only)", ge=0)
    validity: Optional[ValidityEnum] = Field(None, description="New validity (Regular orders only, cannot change to/from IOC)")

    @validator('variety')
    def check_modifiable_variety(cls, v):
        # As per Kite docs, only regular and CO orders can be modified via API
        if v not in [VarietyEnum.REGULAR, VarietyEnum.CO]:
            raise ValueError(f"Modification is not supported for variety '{v.value}'. Only 'regular' and 'co' are allowed.")
        return v

    @validator('validity')
    def check_validity_modification(cls, v, values):
        # Assuming original validity is not available here, but API prevents IOC changes
        if v == ValidityEnum.IOC:
            raise ValueError("Cannot change validity to IOC.")
        # Also cannot change from IOC, but we can't check that here
        return v

    @validator('parent_order_id')
    def parent_order_id_for_co(cls, v, values):
        # Parent order ID is typically needed when modifying the second leg (SL/TP) of a CO order
        # The API might require it conditionally, but validation here is complex without knowing which leg is being modified.
        # We allow it optionally.
        return v

class CancelOrderParams(BaseModel):
    variety: VarietyEnum = Field(..., description="Order variety (regular, co, amo, iceberg, auction)")
    order_id: str = Field(..., description="The ID of the order to cancel")
    parent_order_id: Optional[str] = Field(None, description="Parent order ID if cancelling a second-leg CO order")

# --- Response / Error Models --- 

class OrderIDResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID assigned by the exchange/broker.")

class KiteApiError(BaseModel):
    error_type: str = Field(..., description="The type of error encountered.")
    message: str = Field(..., description="A descriptive error message.")
