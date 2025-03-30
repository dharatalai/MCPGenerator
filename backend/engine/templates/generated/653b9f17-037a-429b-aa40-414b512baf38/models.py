from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator

# Define common types
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: VarietyType = Field(..., description="Order variety")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument")
    exchange: ExchangeType = Field(..., description="Name of the exchange")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    order_type: OrderType = Field(..., description="Order type")
    quantity: int = Field(..., description="Quantity to transact", gt=0)
    product: ProductType = Field(..., description="Product type")
    price: Optional[float] = Field(None, description="The price for LIMIT orders", ge=0)
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders", ge=0)
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades)", ge=0)
    validity: ValidityType = Field(..., description="Order validity")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders", ge=1)
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10)", ge=2, le=10)
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order", ge=1)
    auction_number: Optional[str] = Field(None, description="Unique identifier for a particular auction")
    tag: Optional[str] = Field(None, description="Optional tag for the order (max 20 chars)", max_length=20)

    @validator('price', always=True)
    def check_price_for_limit(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') != 'LIMIT' and v is not None:
            # Kite API might ignore it, but better to be explicit
            # raise ValueError('Price is only applicable for LIMIT orders')
            pass # Allow sending price even if not LIMIT, API might handle it
        return v

    @validator('trigger_price', always=True)
    def check_trigger_price(cls, v, values):
        if values.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        if values.get('order_type') not in ['SL', 'SL-M'] and v is not None:
            # raise ValueError('Trigger price is only applicable for SL and SL-M orders')
            pass # Allow sending trigger_price, API might handle it (e.g., for CO)
        return v

    @validator('validity_ttl', always=True)
    def check_validity_ttl(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if values.get('validity') != 'TTL' and v is not None:
            raise ValueError('validity_ttl is only applicable for TTL validity')
        return v

    @validator('iceberg_legs', 'iceberg_quantity', always=True)
    def check_iceberg_params(cls, v, values, field):
        if values.get('variety') == 'iceberg':
            if field.name == 'iceberg_legs' and v is None:
                raise ValueError('iceberg_legs is required for iceberg orders')
            if field.name == 'iceberg_quantity' and v is None:
                raise ValueError('iceberg_quantity is required for iceberg orders')
        elif v is not None:
            raise ValueError(f'{field.name} is only applicable for iceberg orders')
        return v

    @validator('auction_number', always=True)
    def check_auction_number(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction orders')
        if values.get('variety') != 'auction' and v is not None:
            raise ValueError('auction_number is only applicable for auction orders')
        return v

class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order."""
    variety: VarietyType = Field(..., description="Order variety")
    order_id: str = Field(..., description="The ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="Required for second leg CO modification")
    # Fields below are optional and depend on variety/context
    order_type: Optional[OrderType] = Field(None, description="New order type (regular variety)")
    quantity: Optional[int] = Field(None, description="New quantity (regular variety)", gt=0)
    price: Optional[float] = Field(None, description="New price (for LIMIT/CO orders)", ge=0)
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL/SL-M/CO orders)", ge=0)
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (regular variety)", ge=0)
    validity: Optional[ValidityType] = Field(None, description="New validity (regular variety)")

    @validator('parent_order_id', always=True)
    def check_parent_order_id(cls, v, values):
        # Basic check, actual requirement might depend on API state/context
        if values.get('variety') == 'co' and v is None:
            # This might only be needed for modifying the *second leg* of a CO
            # Adding a warning or allowing it might be better than strict validation here
            pass
        return v

class CancelOrderParams(BaseModel):
    """Parameters for cancelling an order."""
    variety: VarietyType = Field(..., description="Order variety")
    order_id: str = Field(..., description="The ID of the order to cancel")
    parent_order_id: Optional[str] = Field(None, description="Required for second leg CO cancellation")

    @validator('parent_order_id', always=True)
    def check_parent_order_id(cls, v, values):
        # Basic check, actual requirement might depend on API state/context
        if values.get('variety') == 'co' and v is None:
            # This might only be needed for cancelling the *second leg* of a CO
            pass
        return v

class KiteResponse(BaseModel):
    """Standard response structure from Kite Connect API calls."""
    status: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error_type: Optional[str] = None
