from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order.

    Corresponds to the input model for the 'place_order' tool.
    """
    variety: str = Field(..., description="Order variety (regular, amo, co, iceberg, auction). This will be part of the URL path.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY23JUL18000CE').")
    exchange: str = Field(..., description="Name of the exchange (e.g., NSE, BSE, NFO, CDS, BCD, MCX).")
    transaction_type: str = Field(..., description="Transaction type: 'BUY' or 'SELL'.")
    order_type: str = Field(..., description="Order type: 'MARKET', 'LIMIT', 'SL', 'SL-M'.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: str = Field(..., description="Product type: 'CNC', 'NRML', 'MIS', 'MTF'.")
    validity: str = Field(..., description="Order validity: 'DAY', 'IOC', 'TTL'.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders. Also used for CO.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required for variety='iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg (quantity/iceberg_legs). Required for variety='iceberg'.")
    auction_number: Optional[str] = Field(None, description="Unique identifier for a specific auction. Required for variety='auction'.")
    tag: Optional[str] = Field(None, max_length=20, description="Optional tag for the order (alphanumeric, max 20 chars).")

    @validator('transaction_type')
    def transaction_type_must_be_buy_or_sell(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError('transaction_type must be BUY or SELL')
        return v.upper()

    @validator('order_type')
    def order_type_must_be_valid(cls, v):
        if v.upper() not in ['MARKET', 'LIMIT', 'SL', 'SL-M']:
            raise ValueError('order_type must be MARKET, LIMIT, SL, or SL-M')
        return v.upper()

    @validator('validity')
    def validity_must_be_valid(cls, v):
        if v.upper() not in ['DAY', 'IOC', 'TTL']:
            raise ValueError('validity must be DAY, IOC, or TTL')
        return v.upper()

    @validator('product')
    def product_must_be_valid(cls, v):
        if v.upper() not in ['CNC', 'NRML', 'MIS', 'MTF']:
            raise ValueError('product must be CNC, NRML, MIS, or MTF')
        return v.upper()

    @validator('price')
    def price_required_for_limit(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('price is required for LIMIT orders')
        if values.get('order_type') != 'LIMIT' and v is not None:
             # Kite API might ignore it, but better to be explicit
             pass # Allow price for non-limit, though it might be ignored by API
        return v

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        order_type = values.get('order_type')
        variety = values.get('variety')
        if order_type in ['SL', 'SL-M'] and v is None:
            raise ValueError('trigger_price is required for SL/SL-M orders')
        if variety == 'co' and v is None:
            raise ValueError('trigger_price is required for CO orders')
        return v

    @validator('validity_ttl')
    def validity_ttl_required_for_ttl(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        return v

    @validator('iceberg_legs')
    def iceberg_legs_required_for_iceberg(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_legs is required for iceberg variety')
        if v is not None and not (2 <= v <= 10):
             raise ValueError('iceberg_legs must be between 2 and 10')
        return v

    @validator('iceberg_quantity')
    def iceberg_quantity_required_for_iceberg(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_quantity is required for iceberg variety')
        # Add check: iceberg_quantity * iceberg_legs == quantity ? Maybe too strict, API handles this.
        return v

    @validator('auction_number')
    def auction_number_required_for_auction(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction variety')
        return v

class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order.

    Corresponds to the input model for the 'modify_order' tool.
    """
    variety: str = Field(..., description="Variety of the order to modify (e.g., 'regular', 'co'). Path parameter.")
    order_id: str = Field(..., description="The ID of the order to modify. Path parameter.")
    parent_order_id: Optional[str] = Field(None, description="ID of the parent order (required for modifying second-leg CO orders).")
    order_type: Optional[str] = Field(None, description="New order type (e.g., 'LIMIT', 'MARKET').")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity.")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity.")
    validity: Optional[str] = Field(None, description="New validity ('DAY', 'IOC').")

    @validator('order_type')
    def order_type_must_be_valid(cls, v):
        if v is not None and v.upper() not in ['MARKET', 'LIMIT', 'SL', 'SL-M']:
            raise ValueError('order_type must be MARKET, LIMIT, SL, or SL-M')
        return v.upper() if v else None

    @validator('validity')
    def validity_must_be_valid(cls, v):
        if v is not None and v.upper() not in ['DAY', 'IOC']:
            raise ValueError('validity must be DAY or IOC')
        return v.upper() if v else None

    @validator('price')
    def price_check_with_order_type(cls, v, values):
        # If order_type is being changed to LIMIT, price might become required
        # If order_type is being changed away from LIMIT, price might become irrelevant
        # API likely handles this, so basic validation is sufficient here.
        if values.get('order_type') == 'LIMIT' and v is None:
            # This might be okay if the original order was LIMIT and price isn't changing
            # Let the API handle this specific validation case during modification
            pass
        return v

    @validator('trigger_price')
    def trigger_price_check_with_order_type(cls, v, values):
        # Similar logic as price - API validation is more robust for modifications
        order_type = values.get('order_type')
        if order_type in ['SL', 'SL-M'] and v is None:
            # Might be okay if not changing trigger_price
            pass
        return v

# Although the plan specifies Dict[str, str], a model provides better structure if needed later.
class OrderResponse(BaseModel):
    order_id: str
