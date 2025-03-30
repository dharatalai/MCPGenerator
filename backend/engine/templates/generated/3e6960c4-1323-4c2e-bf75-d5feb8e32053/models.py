from typing import Optional, Literal, Dict
from pydantic import BaseModel, Field, validator, root_validator

# Define common types used across models
OrderVariety = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
Exchange = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order.

    Corresponds to the input needed for the place_order tool.
    """
    variety: OrderVariety = Field(..., description="The variety of the order.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'ACC', 'SBIN').")
    exchange: Exchange = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Type of order.")
    quantity: int = Field(..., gt=0, description="Quantity to transact. Must be positive.")
    product: ProductType = Field(..., description="Product type (CNC, NRML, MIS, MTF).")
    price: Optional[float] = Field(None, description="The price for LIMIT orders. Required if order_type is LIMIT or SL.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders. Required if order_type is SL or SL-M. For CO orders, this is the stoploss trigger price.")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="Quantity to disclose publicly (for equity trades). Defaults to 0 if None.")
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders. Required if validity is TTL.")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order (2-10). Required for variety='iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg (quantity/iceberg_legs). Auto-calculated if not provided for variety='iceberg'.")
    auction_number: Optional[str] = Field(None, description="Unique identifier for a specific auction. Required for variety='auction'.")
    tag: Optional[str] = Field(None, max_length=20, description="Optional tag for the order (alphanumeric, max 20 chars).")

    @root_validator(pre=False, skip_on_failure=True)
    def check_conditional_required_fields(cls, values):
        order_type = values.get('order_type')
        price = values.get('price')
        trigger_price = values.get('trigger_price')
        validity = values.get('validity')
        validity_ttl = values.get('validity_ttl')
        variety = values.get('variety')
        iceberg_legs = values.get('iceberg_legs')
        auction_number = values.get('auction_number')

        if order_type in ['LIMIT', 'SL'] and price is None:
            raise ValueError("price is required for LIMIT and SL order types")
        if order_type in ['SL', 'SL-M'] and trigger_price is None:
            raise ValueError("trigger_price is required for SL and SL-M order types")
        if variety == 'co' and trigger_price is None:
            # CO orders require a trigger price (stoploss)
            raise ValueError("trigger_price is required for CO variety")
        if validity == 'TTL' and validity_ttl is None:
            raise ValueError("validity_ttl is required when validity is TTL")
        if variety == 'iceberg' and iceberg_legs is None:
            raise ValueError("iceberg_legs is required for iceberg variety")
        if variety == 'auction' and auction_number is None:
            raise ValueError("auction_number is required for auction variety")

        return values

    class Config:
        use_enum_values = True # Ensure Literal values are used directly


class ModifyOrderParams(BaseModel):
    """Parameters for modifying a pending order.

    Corresponds to the input needed for the modify_order tool.
    """
    variety: OrderVariety = Field(..., description="The variety of the order to modify.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    order_type: Optional[OrderType] = Field(None, description="New order type (only for regular variety).")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (only for regular variety). Must be positive if provided.")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders - regular/co variety).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders).")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="New disclosed quantity (only for regular variety, equity). Defaults to 0 if None.")
    validity: Optional[ValidityType] = Field(None, description="New validity (only for regular variety).")

    @root_validator(pre=False, skip_on_failure=True)
    def check_modify_conditions(cls, values):
        variety = values.get('variety')
        order_type = values.get('order_type')
        quantity = values.get('quantity')
        disclosed_quantity = values.get('disclosed_quantity')
        validity = values.get('validity')

        # Restrictions based on Kite Connect documentation for modifications
        if variety != 'regular':
            if order_type is not None:
                raise ValueError(f"order_type cannot be modified for {variety} variety")
            if quantity is not None:
                raise ValueError(f"quantity cannot be modified for {variety} variety")
            if disclosed_quantity is not None:
                raise ValueError(f"disclosed_quantity cannot be modified for {variety} variety")
            if validity is not None:
                raise ValueError(f"validity cannot be modified for {variety} variety")

        return values

    class Config:
        use_enum_values = True


class OrderResponse(BaseModel):
    """Standard response structure for successful order placement or modification.

    Contains the order ID.
    """
    order_id: str = Field(..., description="The unique identifier for the order.")
