from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

# --- Input Models ---

class PlaceOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="Transaction type")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type")
    quantity: int = Field(..., gt=0, description="Quantity to transact")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product type")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders)")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades)")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field("DAY", description="Order validity. Default is DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Total number of legs for iceberg order type (2-10)")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs)")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction (for auction orders)")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag to apply to an order (alphanumeric, max 20 chars)")

    class Config:
        extra = 'forbid' # Prevent unexpected fields

class ModifyOrderParams(BaseModel):
    variety: Literal['regular', 'co'] = Field(..., description="Order variety")
    order_id: str = Field(..., description="The ID of the order to modify")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (only for regular orders)")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (only for regular orders)")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders)")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only for regular equity orders)")
    validity: Optional[Literal['DAY', 'IOC']] = Field(None, description="New validity (only for regular orders, e.g., DAY)") # TTL not allowed for modification

    class Config:
        extra = 'forbid'

class CancelOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety")
    order_id: str = Field(..., description="The ID of the order to cancel")
    parent_order_id: Optional[str] = Field(None, description="Required for cancelling second-leg CO orders")

    class Config:
        extra = 'forbid'

# --- Output/Response Models ---

class OrderResponse(BaseModel):
    order_id: str = Field(..., description="The unique order ID")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="General error message")
    status_code: Optional[int] = Field(None, description="HTTP status code, if applicable")
    details: Optional[Any] = Field(None, description="Additional error details from the API or system")
