from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator

# Define Literal types for constrained fields
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']
ModifiableVarietyType = Literal['regular', 'co'] # Based on plan description
ModifiableOrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ModifiableValidityType = Literal['DAY', 'IOC', 'TTL']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order.

    Corresponds to the input model for the 'place_order' tool.
    """
    variety: VarietyType = Field(..., description="Order variety type.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product type (margin product).")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders).", ge=0)
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders).", ge=0)
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).", ge=0)
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.", ge=1)
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10).", ge=2, le=10)
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs).", ge=1)
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction.")
    tag: Optional[str] = Field(None, description="An optional tag to apply to an order (alphanumeric, max 20 chars).", max_length=20)

    @root_validator
    def check_conditional_required_fields(cls, values):
        order_type = values.get('order_type')
        price = values.get('price')
        trigger_price = values.get('trigger_price')
        validity = values.get('validity')
        validity_ttl = values.get('validity_ttl')
        variety = values.get('variety')
        iceberg_legs = values.get('iceberg_legs')
        iceberg_quantity = values.get('iceberg_quantity')
        quantity = values.get('quantity')
        auction_number = values.get('auction_number')

        if order_type == 'LIMIT' and price is None:
            raise ValueError("Price is required for LIMIT orders.")
        if order_type in ('SL', 'SL-M') and trigger_price is None:
            raise ValueError("Trigger price is required for SL and SL-M orders.")
        if validity == 'TTL' and validity_ttl is None:
            raise ValueError("validity_ttl is required for TTL validity.")
        if variety == 'iceberg' and (iceberg_legs is None or iceberg_quantity is None):
            raise ValueError("iceberg_legs and iceberg_quantity are required for iceberg orders.")
        if variety == 'auction' and auction_number is None:
            raise ValueError("auction_number is required for auction orders.")

        if iceberg_legs and iceberg_quantity and quantity:
            if quantity % iceberg_legs != 0:
                raise ValueError("Quantity must be a multiple of iceberg_legs.")
            if iceberg_quantity != quantity // iceberg_legs:
                raise ValueError("iceberg_quantity must be equal to quantity / iceberg_legs.")

        return values

    class Config:
        use_enum_values = True # Ensure literals are passed as strings

class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order.

    Corresponds to the input model for the 'modify_order' tool.
    """
    variety: ModifiableVarietyType = Field(..., description="Order variety type ('regular' or 'co').")
    order_id: str = Field(..., description="The ID of the order to modify.")
    order_type: Optional[ModifiableOrderType] = Field(None, description="New order type (for regular orders).")
    quantity: Optional[int] = Field(None, description="New quantity (for regular orders).", gt=0)
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).", ge=0)
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, LIMIT CO orders).", ge=0)
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (for regular equity orders).", ge=0)
    validity: Optional[ModifiableValidityType] = Field(None, description="New validity (for regular orders).")

    @root_validator
    def check_at_least_one_modifiable_field(cls, values):
        modifiable_fields = ['order_type', 'quantity', 'price', 'trigger_price', 'disclosed_quantity', 'validity']
        if not any(values.get(field) is not None for field in modifiable_fields):
            raise ValueError("At least one field (order_type, quantity, price, trigger_price, disclosed_quantity, validity) must be provided for modification.")
        return values

    # Add further validation if needed, e.g., price required if modifying to LIMIT

    class Config:
        use_enum_values = True

class CancelOrderParams(BaseModel):
    """Parameters for cancelling an order.

    Corresponds to the input model for the 'cancel_order' tool.
    """
    variety: VarietyType = Field(..., description="Order variety type.")
    order_id: str = Field(..., description="The ID of the order to cancel.")

    class Config:
        use_enum_values = True

class OrderResponseData(BaseModel):
    """Data part of a successful order response."""
    order_id: str

class OrderResponse(BaseModel):
    """Standard response structure for order operations."""
    status: Literal['success']
    data: OrderResponseData

class ErrorResponse(BaseModel):
    """Standard error response structure."""
    status: Literal['error']
    message: str
    details: Optional[Dict[str, Any]] = None
