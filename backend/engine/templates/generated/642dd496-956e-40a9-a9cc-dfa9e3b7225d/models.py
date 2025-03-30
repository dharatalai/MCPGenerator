from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator

# Define Literal types for common parameters
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ModifyVarietyType = Literal['regular', 'co']

class PlaceOrderParams(BaseModel):
    """Input model for the place_order tool."""
    variety: VarietyType = Field(..., description="The variety of the order.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: ExchangeType = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: ProductType = Field(..., description="Product margin type.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (equity only).", ge=0)
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.", gt=0)
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10).", ge=2, le=10)
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs).", gt=0)
    auction_number: Optional[str] = Field(None, description="Unique identifier for a specific auction.")
    tag: Optional[str] = Field(None, description="Optional tag for the order (alphanumeric, max 20 chars).", max_length=20)

    @root_validator
    def check_conditional_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate conditional requirements based on order type, variety, etc."""
        order_type = values.get('order_type')
        price = values.get('price')
        trigger_price = values.get('trigger_price')
        variety = values.get('variety')
        validity = values.get('validity')
        validity_ttl = values.get('validity_ttl')
        iceberg_legs = values.get('iceberg_legs')
        iceberg_quantity = values.get('iceberg_quantity')
        quantity = values.get('quantity')
        auction_number = values.get('auction_number')

        if order_type == 'LIMIT' and price is None:
            raise ValueError("Price is required for LIMIT orders.")
        if order_type in ['SL', 'SL-M'] and trigger_price is None:
            raise ValueError("Trigger price is required for SL and SL-M orders.")
        if variety == 'co' and trigger_price is None:
             # CO Market needs trigger price relative to LTP, CO Limit needs it too
             pass # Kiteconnect library handles specific CO logic, basic check here
        if validity == 'TTL' and validity_ttl is None:
            raise ValueError("validity_ttl is required for TTL validity.")
        if variety == 'iceberg' and (iceberg_legs is None or iceberg_quantity is None):
            raise ValueError("iceberg_legs and iceberg_quantity are required for iceberg orders.")
        if variety == 'iceberg' and iceberg_quantity and iceberg_legs and quantity:
            # Approximate check, exact validation might depend on broker rules
            if not (quantity / iceberg_legs) >= iceberg_quantity:
                 pass # Let API handle exact validation, avoid complex client-side rules
        if variety == 'auction' and auction_number is None:
            raise ValueError("auction_number is required for auction orders.")

        # Prevent price/trigger_price for MARKET orders if not needed by variety (e.g., regular MARKET)
        if order_type == 'MARKET' and variety == 'regular':
            if price is not None:
                raise ValueError("Price should not be provided for regular MARKET orders.")
            # Trigger price might be used in AMO SL-M orders, so allow it generally
            # if trigger_price is not None:
            #     raise ValueError("Trigger price should not be provided for regular MARKET orders.")

        return values

class ModifyOrderParams(BaseModel):
    """Input model for the modify_order tool."""
    variety: ModifyVarietyType = Field(..., description="The variety of the order to modify ('regular' or 'co').")
    order_id: str = Field(..., description="The ID of the order to modify.")
    order_type: Optional[OrderType] = Field(None, description="New order type (Regular variety only).")
    quantity: Optional[int] = Field(None, description="New quantity (Regular variety only).", gt=0)
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO LIMIT orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (Regular variety only).", ge=0)
    validity: Optional[ValidityType] = Field(None, description="New validity (Regular variety only).")

    @root_validator
    def check_regular_only_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure fields only applicable to 'regular' variety are not set for 'co'."""
        variety = values.get('variety')
        if variety == 'co':
            # Fields not modifiable for CO orders according to general Kite docs
            if values.get('order_type') is not None:
                raise ValueError("order_type cannot be modified for CO orders.")
            if values.get('quantity') is not None:
                raise ValueError("quantity cannot be modified for CO orders.")
            if values.get('disclosed_quantity') is not None:
                raise ValueError("disclosed_quantity cannot be modified for CO orders.")
            if values.get('validity') is not None:
                raise ValueError("validity cannot be modified for CO orders.")
        elif variety == 'regular':
            # Validate conditions for regular order modification
            order_type = values.get('order_type')
            price = values.get('price')
            trigger_price = values.get('trigger_price')

            if order_type == 'LIMIT' and price is None and values.get('price') is None:
                 # If modifying to LIMIT, price must be provided. If already LIMIT, price is optional.
                 # This logic is complex without knowing the original order state. Let API handle.\
                 pass
            if order_type in ['SL', 'SL-M'] and trigger_price is None and values.get('trigger_price') is None:
                 # Similar complexity as above. Let API handle.\
                 pass
        return values

# Example Response Structure (as per plan, tools return Dict[str, Any])
class OrderResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
