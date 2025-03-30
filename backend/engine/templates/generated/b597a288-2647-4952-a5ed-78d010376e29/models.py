from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

class PlaceOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="BUY or SELL")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type")
    quantity: int = Field(..., description="Quantity to transact")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product code")
    price: Optional[float] = Field(None, description="The price to execute the order at (for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (for SL, SL-M orders)")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades)")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field('DAY', description="Order validity. Default is DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10)")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs)")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction (for auction variety)")
    tag: Optional[str] = Field(None, description="An optional tag to apply to an order (alphanumeric, max 20 chars)")

class ModifyOrderParams(BaseModel):
    variety: Literal['regular', 'co'] = Field(..., description="Order variety")
    order_id: str = Field(..., description="The ID of the order to modify")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID (required for modifying second leg of CO)")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (only for regular variety)")
    quantity: Optional[int] = Field(None, description="New quantity (only for regular variety)")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders)")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, or LIMIT CO orders)")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (only for regular variety)")
    validity: Optional[Literal['DAY', 'IOC']] = Field(None, description="New validity (only for regular variety, DAY or IOC)")

class CancelOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety")
    order_id: str = Field(..., description="The ID of the order to cancel")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID (required for cancelling second leg of CO)")

class OrderResponse(BaseModel):
    order_id: str

class SuccessResponse(BaseModel):
    status: str = "success"
    data: OrderResponse

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    error_type: Optional[str] = None
