from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Literal types for Zerodha API parameters
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']
ModifyVarietyType = Literal['regular', 'co'] # Modify only supports these

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: VarietyType = Field(..., description="Order variety.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product type.")
    validity: ValidityType = Field(..., description="Order validity.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="Trigger price for SL/SL-M orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity.")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total legs for iceberg order (2-10).")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg.")
    auction_number: Optional[str] = Field(None, description="Unique identifier for auction orders.")
    tag: Optional[str] = Field(None, max_length=20, description="Optional order tag (alphanumeric, max 20 chars).")

    @field_validator('price')
    def check_price_for_limit(cls, v, values):
        data = values.data
        if data.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if data.get('order_type') == 'MARKET' and v is not None:
             # Kite API ignores price for MARKET orders, but good to be explicit
             # raise ValueError('Price should not be provided for MARKET orders')
             pass # Allow it, API might handle it gracefully
        return v

    @field_validator('trigger_price')
    def check_trigger_price(cls, v, values):
        data = values.data
        if data.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        return v

    @field_validator('validity_ttl')
    def check_validity_ttl(cls, v, values):
        data = values.data
        if data.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if data.get('validity') != 'TTL' and v is not None:
            raise ValueError('validity_ttl is only applicable for TTL validity')
        return v

    @field_validator('iceberg_legs', 'iceberg_quantity')
    def check_iceberg_params(cls, v, info):
        values = info.data
        field_name = info.field_name
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError(f'{field_name} is required for iceberg orders')
        if values.get('variety') != 'iceberg' and v is not None:
            raise ValueError(f'{field_name} is only applicable for iceberg orders')
        return v

    @field_validator('auction_number')
    def check_auction_number(cls, v, values):
        data = values.data
        if data.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction orders')
        if data.get('variety') != 'auction' and v is not None:
            raise ValueError('auction_number is only applicable for auction orders')
        return v

class ModifyRegularOrderParams(BaseModel):
    """Parameters for modifying a regular or CO order."""
    variety: ModifyVarietyType = Field(..., description="Order variety ('regular' or 'co').")
    order_id: str = Field(..., description="The ID of the order to modify.")
    # Fields applicable only for 'regular' variety modification
    order_type: Optional[OrderType] = Field(None, description="New order type (regular only).")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (regular only).")
    validity: Optional[ValidityType] = Field(None, description="New order validity (regular only).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (regular only).")
    # Fields applicable for both 'regular' and 'co' modification
    price: Optional[float] = Field(None, description="New price (LIMIT/SL orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (SL/SL-M/CO orders).")

    @field_validator('order_type', 'quantity', 'validity', 'disclosed_quantity')
    def check_regular_only_fields(cls, v, info):
        values = info.data
        field_name = info.field_name
        if values.get('variety') == 'co' and v is not None:
            raise ValueError(f'{field_name} cannot be modified for CO orders.')
        return v

class CancelOrderParams(BaseModel):
    """Parameters for cancelling an order."""
    variety: VarietyType = Field(..., description="Order variety.")
    order_id: str = Field(..., description="The ID of the order to cancel.")

class GetOrdersParams(BaseModel):
    """Parameters for retrieving all orders (no specific params needed)."""
    pass # No parameters required for this endpoint

class GetOrderHistoryParams(BaseModel):
    """Parameters for retrieving the history of a specific order."""
    order_id: str = Field(..., description="The ID of the order whose history is to be retrieved.")

class GetTradesParams(BaseModel):
    """Parameters for retrieving all trades (no specific params needed)."""
    pass # No parameters required for this endpoint

class GetOrderTradesParams(BaseModel):
    """Parameters for retrieving trades for a specific order."""
    order_id: str = Field(..., description="The ID of the order whose trades are to be retrieved.")

# Generic response models (optional, but good practice)
class KiteResponseData(BaseModel):
    order_id: Optional[str] = None
    # Add other potential fields if needed

class KiteResponse(BaseModel):
    status: str
    data: Optional[Any] = None # Can be Dict, List[Dict], etc.
    message: Optional[str] = None
    error_type: Optional[str] = None
