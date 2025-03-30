from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict

# Define Literal types for common parameters
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']
ModifyVarietyType = Literal['regular', 'co']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: VarietyType = Field(..., description="Order variety.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product code.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required if variety is 'iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order. Required if variety is 'iceberg'.")
    auction_number: Optional[str] = Field(None, description="Unique identifier for a particular auction. Required if variety is 'auction'.")
    tag: Optional[str] = Field(None, max_length=20, description="Optional tag for the order (alphanumeric, max 20 chars).")

    @validator('price')
    def price_required_for_limit(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') != 'LIMIT' and v is not None:
             # Kite API might ignore it, but good practice to warn or clear
             # print("Warning: Price is only applicable for LIMIT orders.")
             return None # Or return v if API handles it
        return v

    @validator('trigger_price')
    def trigger_price_required_for_sl(cls, v, values):
        if values.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        if values.get('order_type') not in ['SL', 'SL-M'] and v is not None:
            # print("Warning: Trigger price is only applicable for SL/SL-M orders.")
            return None # Or return v
        return v

    @validator('validity_ttl')
    def validity_ttl_required(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required when validity is TTL')
        if values.get('validity') != 'TTL' and v is not None:
            return None
        return v

    @validator('iceberg_legs')
    def iceberg_legs_required(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_legs is required when variety is iceberg')
        if values.get('variety') != 'iceberg' and v is not None:
            return None
        if v is not None and not (2 <= v <= 10):
             raise ValueError('iceberg_legs must be between 2 and 10')
        return v

    @validator('iceberg_quantity')
    def iceberg_quantity_required(cls, v, values):
        if values.get('variety') == 'iceberg' and v is None:
            raise ValueError('iceberg_quantity is required when variety is iceberg')
        if values.get('variety') != 'iceberg' and v is not None:
            return None
        # Add validation for iceberg_quantity relative to total quantity if needed
        # if v is not None and values.get('quantity') is not None and values.get('iceberg_legs') is not None:
        #     if v * values['iceberg_legs'] < values['quantity']:
        #         raise ValueError('iceberg_quantity * iceberg_legs must be >= total quantity')
        return v

    @validator('auction_number')
    def auction_number_required(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required when variety is auction')
        if values.get('variety') != 'auction' and v is not None:
            return None
        return v


class ModifyOrderParams(BaseModel):
    """Parameters for modifying a pending order."""
    variety: ModifyVarietyType = Field(..., description="Order variety. Currently supports 'regular' and 'co'.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    # Fields below are optional for modification
    order_type: Optional[OrderType] = Field(None, description="New order type (Regular only).")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (Regular only).")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders, Regular/CO).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (Regular only). Not applicable for CO.")
    validity: Optional[ValidityType] = Field(None, description="New validity (Regular only). Not applicable for CO.")

    @validator('order_type', 'quantity', 'disclosed_quantity', 'validity')
    def regular_only_fields(cls, v, field, values):
        if values.get('variety') == 'co' and v is not None:
            raise ValueError(f"{field.name} cannot be modified for CO orders.")
        return v

    @validator('price')
    def modify_price_check(cls, v, values):
        # Price can be modified for LIMIT orders (Regular/CO)
        # If changing to LIMIT, price might become required (handled by API or needs more complex validation)
        return v

    @validator('trigger_price')
    def modify_trigger_price_check(cls, v, values):
        # Trigger price can be modified for SL, SL-M (Regular) and CO orders
        return v

class CancelOrderParams(BaseModel):
    """Parameters for cancelling an order."""
    variety: VarietyType = Field(..., description="Order variety.")
    order_id: str = Field(..., description="The ID of the order to cancel.")

class OrderResponse(BaseModel):
    """Standard response format for successful order operations."""
    order_id: str = Field(..., description="The unique order ID.")
