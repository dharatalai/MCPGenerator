from pydantic import BaseModel, Field
from typing import Optional, Literal

# --- Parameter Models ---

class GenerateSessionParams(BaseModel):
    request_token: str = Field(..., description="One-time token obtained after the login flow.")

class PlaceOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety.")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="Transaction type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product type.")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders. Required if order_type is LIMIT.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders. Required if order_type is SL or SL-M.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity).")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field('DAY', description="Order validity. Default is DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity. Required if validity is TTL.")
    iceberg_legs: Optional[int] = Field(None, ge=2, le=10, description="Number of legs for iceberg order (2-10). Required if variety is iceberg.")
    iceberg_quantity: Optional[int] = Field(None, description="Quantity for each iceberg leg. Required if variety is iceberg.")
    auction_number: Optional[str] = Field(None, description="Auction number for auction orders. Required if variety is auction.")
    tag: Optional[str] = Field(None, max_length=20, description="Optional tag for the order (max 20 chars).")

    # Basic validation - more complex cross-field validation might be needed
    # depending on KiteConnect API rules (e.g., price required for LIMIT)

class ModifyOrderParams(BaseModel):
    variety: Literal['regular', 'co'] = Field(..., description="Order variety (regular, co).")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="The parent order ID (required for modifying second leg of CO).")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity.")
    price: Optional[float] = Field(None, description="New price (for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders).")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (only applicable for certain modifications, e.g., SL to LIMIT). Check API docs.")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity.")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field(None, description="New validity (only applicable for regular orders, e.g., DAY to TTL). Check API docs.")

# --- Return Models (Optional but good practice) ---
# While the tools currently return Dict[str, Any], defining specific return models improves clarity.

class SessionData(BaseModel):
    user_id: str
    user_name: str
    user_shortname: str
    avatar_url: Optional[str]
    user_type: str
    email: str
    broker: str
    exchanges: list[str]
    products: list[str]
    order_types: list[str]
    api_key: str
    access_token: str
    public_token: str
    login_time: str # Consider using datetime

class OrderResponse(BaseModel):
    order_id: str
