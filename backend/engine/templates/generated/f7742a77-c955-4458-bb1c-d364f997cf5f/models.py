from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

# --- Input Models ---

class PlaceOrderParams(BaseModel):
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety (regular, amo, co, iceberg, auction). Determines the endpoint path.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange (NSE, BSE, NFO, CDS, BCD, MCX).")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="BUY or SELL.")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M).")
    quantity: int = Field(..., description="Quantity to transact.")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product type (CNC, NRML, MIS, MTF).")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders).")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: Literal['DAY', 'IOC', 'TTL'] = Field('DAY', description="Order validity (DAY, IOC, TTL). Default is DAY.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required for variety='iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs). Required for variety='iceberg'.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required for variety='auction'.")
    tag: Optional[str] = Field(None, description="An optional tag to apply to an order (alphanumeric, max 20 chars).", max_length=20)

class ModifyOrderParams(BaseModel):
    variety: Literal['regular', 'co'] = Field(..., description="Order variety (regular, co). Determines the endpoint path.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="Required for modifying second leg of CO.")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (Only applicable for regular variety).")
    quantity: Optional[int] = Field(None, description="New quantity (Only applicable for regular variety).")
    price: Optional[float] = Field(None, description="New price (applicable for LIMIT orders, CO).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (applicable for SL, SL-M, CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (Only applicable for regular variety).")
    validity: Optional[Literal['DAY', 'IOC']] = Field(None, description="New validity (DAY, IOC) (Only applicable for regular variety).")

class CancelOrderParams(BaseModel):
    variety: Literal['regular', 'co', 'amo', 'iceberg', 'auction'] = Field(..., description="Order variety (regular, co, amo, iceberg, auction). Determines the endpoint path.")
    order_id: str = Field(..., description="The ID of the order to cancel.")
    parent_order_id: Optional[str] = Field(None, description="Required for cancelling second leg of CO.")

class GetOrdersParams(BaseModel):
    # No parameters needed for get_orders
    pass

class GetOrderHistoryParams(BaseModel):
    order_id: str = Field(..., description="The ID of the order to retrieve history for.")

class GetTradesParams(BaseModel):
    # No parameters needed for get_trades
    pass

class GetOrderTradesParams(BaseModel):
    order_id: str = Field(..., description="The ID of the order to retrieve trades for.")

# --- Response Models (Informational - Tools return Dict/List as per spec) ---
# These models represent the expected structure but are not strictly enforced
# in the tool return types based on the current implementation plan.

class Order(BaseModel):
    order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    placed_by: Optional[str] = None
    variety: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    status_message_raw: Optional[str] = None
    order_timestamp: Optional[str] = None # Consider datetime
    exchange_update_timestamp: Optional[str] = None # Consider datetime
    exchange_timestamp: Optional[str] = None # Consider datetime
    tradingsymbol: Optional[str] = None
    instrument_token: Optional[int] = None
    exchange: Optional[str] = None
    transaction_type: Optional[str] = None
    order_type: Optional[str] = None
    product: Optional[str] = None
    validity: Optional[str] = None
    validity_ttl: Optional[int] = None
    quantity: Optional[int] = None
    disclosed_quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    average_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    pending_quantity: Optional[int] = None
    cancelled_quantity: Optional[int] = None
    market_protection: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None
    tag: Optional[str] = None
    guid: Optional[str] = None

class Trade(BaseModel):
    trade_id: Optional[str] = None
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    tradingsymbol: Optional[str] = None
    instrument_token: Optional[int] = None
    exchange: Optional[str] = None
    product: Optional[str] = None
    transaction_type: Optional[str] = None
    order_type: Optional[str] = None
    quantity: Optional[int] = None
    average_price: Optional[float] = None
    price: Optional[float] = None # Individual trade price
    fill_timestamp: Optional[str] = None # Consider datetime
    exchange_timestamp: Optional[str] = None # Consider datetime

# --- Error Response Model ---

class KiteApiErrorResponse(BaseModel):
    error_type: str = Field(..., description="The type of error encountered (e.g., AuthenticationError, InputValidationError, OrderException, NetworkError, ServerError).")
    message: str = Field(..., description="A descriptive error message.")
    status_code: Optional[int] = Field(None, description="The HTTP status code returned by the API, if available.")
