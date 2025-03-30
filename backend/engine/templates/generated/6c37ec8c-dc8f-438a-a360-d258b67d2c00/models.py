from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal, Any

# --- Input Models ---

class PlaceOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="The variety of the order.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange.")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="Transaction type.")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type.")
    quantity: int = Field(..., description="Quantity to transact.")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product code.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: Literal['DAY', 'IOC', 'TTL'] = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required if variety is 'iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs). Required if variety is 'iceberg'.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required if variety is 'auction'.")
    tag: Optional[str] = Field(None, description="An optional tag for the order (alphanumeric, max 20 chars).")

class ModifyOrderParams(BaseModel):
    variety: Literal['regular', 'co'] = Field(..., description="The variety of the order to modify. Note: Docs only explicitly mention params for 'regular' and 'co'. Other varieties might not be modifiable or require different params.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (for regular variety).")
    quantity: Optional[int] = Field(None, description="New quantity (for regular variety).")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders, applicable to regular and CO).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, LIMIT CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (for regular variety).")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field(None, description="New validity (for regular variety).")

class CancelOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="The variety of the order to cancel.")
    order_id: str = Field(..., description="The ID of the order to cancel.")
    parent_order_id: Optional[str] = Field(None, description="Conditional: The order ID of the parent order (required for cancelling second-leg CO orders).")

class GetOrdersParams(BaseModel):
    # No parameters needed for retrieving all orders
    pass

class GetOrderHistoryParams(BaseModel):
    order_id: str = Field(..., description="The ID of the order to retrieve history for.")

# --- Return Type Placeholders ---
# Define basic structures for return types based on descriptions.
# The actual Kite API response structure might be more complex.

class OrderResponse(BaseModel):
    order_id: str = Field(..., description="The ID of the order affected.")

# Placeholder for a single order structure returned by get_orders
class Order(BaseModel):
    # Add fields based on actual Kite API response for an order
    # Example fields:
    order_id: Optional[str] = None
    status: Optional[str] = None
    tradingsymbol: Optional[str] = None
    exchange: Optional[str] = None
    transaction_type: Optional[str] = None
    order_type: Optional[str] = None
    quantity: Optional[int] = None
    filled_quantity: Optional[int] = None
    average_price: Optional[float] = None
    # ... other fields
    class Config:
        extra = 'allow' # Allow extra fields from API response

# Placeholder for a single order history entry returned by get_order_history
class OrderHistoryEntry(BaseModel):
    # Add fields based on actual Kite API response for order history
    # Example fields:
    order_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    order_timestamp: Optional[str] = None
    # ... other fields
    class Config:
        extra = 'allow' # Allow extra fields from API response
