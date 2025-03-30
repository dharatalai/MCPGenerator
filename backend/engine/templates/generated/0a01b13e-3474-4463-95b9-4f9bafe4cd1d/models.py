from typing import Optional, Literal
from pydantic import BaseModel, Field, validator, root_validator

# --- Common Response Models ---

class OrderIdResponse(BaseModel):
    """Standard response containing an order ID."""
    order_id: str = Field(..., description="The unique order ID.")

# --- Input Models for Tools ---

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY23JULCE')")
    exchange: Literal['NSE', 'BSE', 'NFO', 'MCX', 'CDS', 'BFO'] = Field(..., description="Name of the exchange")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="'BUY' or 'SELL'")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type")
    quantity: int = Field(..., gt=0, description="Quantity to transact")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product type ('CNC', 'NRML', 'MIS', 'MTF')")
    price: Optional[float] = Field(None, description="The price for LIMIT orders")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades)")
    validity: Literal['DAY', 'IOC', 'TTL'] = Field('DAY', description="Order validity ('DAY', 'IOC', 'TTL')")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders (1-120)")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10)")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order")
    auction_number: Optional[str] = Field(None, description="Unique identifier for a specific auction (for auction orders)")
    tag: Optional[str] = Field(None, max_length=20, description="Optional tag for the order (alphanumeric, max 20 chars)")

    @root_validator
    def check_conditional_fields(cls, values):
        order_type = values.get('order_type')
        price = values.get('price')
        trigger_price = values.get('trigger_price')
        validity = values.get('validity')
        validity_ttl = values.get('validity_ttl')
        variety = values.get('variety')
        iceberg_legs = values.get('iceberg_legs')
        iceberg_quantity = values.get('iceberg_quantity')
        auction_number = values.get('auction_number')

        if order_type == 'LIMIT' and price is None:
            raise ValueError("Price is required for LIMIT orders")
        if order_type in ('SL', 'SL-M') and trigger_price is None:
            raise ValueError("Trigger price is required for SL and SL-M orders")
        if validity == 'TTL' and validity_ttl is None:
            raise ValueError("validity_ttl is required for TTL validity")
        if validity == 'TTL' and (validity_ttl is None or not (1 <= validity_ttl <= 120)):
             raise ValueError("validity_ttl must be between 1 and 120 for TTL validity")
        if variety == 'iceberg' and (iceberg_legs is None or iceberg_quantity is None):
            raise ValueError("iceberg_legs and iceberg_quantity are required for iceberg orders")
        if variety == 'iceberg' and iceberg_legs is not None and not (2 <= iceberg_legs <= 10):
            raise ValueError("iceberg_legs must be between 2 and 10")
        if variety == 'auction' and auction_number is None:
             raise ValueError("auction_number is required for auction orders")

        # CO specific checks (can add more if needed)
        if variety == 'co' and order_type not in ('LIMIT', 'MARKET'):
            raise ValueError("Cover orders (co) must be MARKET or LIMIT")
        if variety == 'co' and trigger_price is None:
            raise ValueError("Trigger price is required for Cover Orders (co)")

        return values

class ModifyOrderParams(BaseModel):
    """Parameters for modifying a pending order."""
    variety: Literal['regular', 'co'] = Field(..., description="Order variety ('regular', 'co')")
    order_id: str = Field(..., description="The ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID (required for modifying second leg of CO)")
    order_type: Optional[Literal['LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (only for regular orders)")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (only for regular orders)")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders, both regular and CO)")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M regular orders; required for LIMIT CO modification)")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only for regular equity orders)")
    validity: Optional[Literal['DAY', 'IOC']] = Field(None, description="New validity ('DAY', 'IOC') (only for regular orders)")

    @root_validator
    def check_modify_conditions(cls, values):
        variety = values.get('variety')
        parent_order_id = values.get('parent_order_id')
        order_type = values.get('order_type')
        quantity = values.get('quantity')
        price = values.get('price')
        trigger_price = values.get('trigger_price')
        validity = values.get('validity')

        if variety == 'co' and parent_order_id is None:
            # Modifying the main leg of CO
            if order_type is not None or quantity is not None or validity is not None:
                raise ValueError("Cannot modify order_type, quantity, or validity for the main leg of a CO order")
            if price is None and trigger_price is None:
                 raise ValueError("Either price or trigger_price must be provided when modifying a CO order")
        elif variety == 'co' and parent_order_id is not None:
             # Modifying the SL leg of CO
             if order_type is not None or quantity is not None or validity is not None or price is not None:
                 raise ValueError("Only trigger_price can be modified for the second leg of a CO order")
             if trigger_price is None:
                  raise ValueError("trigger_price is required when modifying the second leg of a CO order")

        if variety == 'regular':
            if order_type == 'LIMIT' and price is None:
                # If changing to LIMIT, price is needed. If already LIMIT, price might be optional if not changing it.
                # Kite API might require it anyway, best to include if modifying price.
                pass # Let API handle this potentially complex validation
            if order_type in ('SL', 'SL-M') and trigger_price is None:
                # Similar logic for trigger_price
                pass # Let API handle

        return values
