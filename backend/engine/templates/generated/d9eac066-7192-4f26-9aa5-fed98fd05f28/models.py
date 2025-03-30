from typing import Optional, Literal, Dict, List, Any
from pydantic import BaseModel, Field, conint, constr

# Base Models for API Parameters
class BaseParams(BaseModel):
    class Config:
        extra = 'forbid' # Disallow extra fields

# Models for Tool Inputs
class PlaceOrderParams(BaseParams):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="Transaction type")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type")
    quantity: conint(gt=0) = Field(..., description="Quantity to transact (must be positive)")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product type")
    price: Optional[float] = Field(None, description="The price for LIMIT orders. Required if order_type is LIMIT.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders. Required if order_type is SL or SL-M.")
    disclosed_quantity: Optional[conint(ge=0)] = Field(None, description="Quantity to disclose publicly (equity only, must be non-negative)")
    validity: Literal['DAY', 'IOC', 'TTL'] = Field(..., description="Order validity")
    validity_ttl: Optional[conint(gt=0)] = Field(None, description="Order life span in minutes for TTL validity (must be positive). Required if validity is TTL.")
    iceberg_legs: Optional[conint(ge=2, le=10)] = Field(None, description="Number of legs for iceberg order (2-10). Required if variety is iceberg.")
    iceberg_quantity: Optional[conint(gt=0)] = Field(None, description="Split quantity for each iceberg leg (quantity/iceberg_legs). Required if variety is iceberg.")
    auction_number: Optional[str] = Field(None, description="Unique identifier for auction order. Required if variety is auction.")
    tag: Optional[constr(max_length=20)] = Field(None, description="Optional tag for the order (max 20 chars)")

class ModifyOrderParams(BaseParams):
    variety: Literal['regular', 'co'] = Field(..., description="Order variety to modify")
    order_id: str = Field(..., description="The ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID if modifying a second leg CO order")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (Regular only)")
    quantity: Optional[conint(gt=0)] = Field(None, description="New quantity (Regular only, must be positive)")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders)")
    disclosed_quantity: Optional[conint(ge=0)] = Field(None, description="New disclosed quantity (Regular equity only, must be non-negative)")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field(None, description="New validity (Regular only)")

class CancelOrderParams(BaseParams):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety to cancel")
    order_id: str = Field(..., description="The ID of the order to cancel")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID if cancelling a second leg CO order")

class GetOrdersParams(BaseParams):
    # Currently no parameters needed for get_orders, but define for consistency
    pass

# Models for Tool Outputs / Responses
class OrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID.")

class OrderHistoryResponse(BaseModel):
    orders: List[Dict[str, Any]] = Field(..., description="List of orders for the day.")
