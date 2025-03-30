from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator

# --- Custom Exceptions ---
class KiteConnectError(Exception):
    """Base exception class for Kite Connect client errors."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class InputException(KiteConnectError):
    """Invalid input parameters."""
    pass

class TokenException(KiteConnectError):
    """Authentication failure (invalid API key or access token)."""
    pass

class PermissionException(KiteConnectError):
    """Insufficient permissions for the action."""
    pass

class NetworkException(KiteConnectError):
    """Network connectivity issues with the API."""
    pass

class GeneralException(KiteConnectError):
    """General Kite Connect API errors (e.g., RMS rejections, insufficient funds, order state issues)."""
    pass

class RateLimitException(KiteConnectError):
    """Rate limit exceeded."""
    pass

# --- Input Models ---

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange.")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="Transaction type.")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type.")
    quantity: int = Field(..., gt=0, description="Quantity to transact.")
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product type (margin product).")
    price: Optional[float] = Field(None, description="The price to execute the order at (required for LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="The price at which an order should be triggered (required for SL, SL-M orders).")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: Literal['DAY', 'IOC', 'TTL'] = Field('DAY', description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10).")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction (for auction variety).")
    tag: Optional[str] = Field(None, max_length=20, description="An optional tag (alphanumeric, max 20 chars) to identify the order.")

    @validator('price', always=True)
    def check_price_for_limit(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') != 'LIMIT' and v is not None:
            # Kite might implicitly ignore it, but better to be explicit or validate based on API behavior
            pass # Allow price for other types if API permits, otherwise raise ValueError
        return v

    @validator('trigger_price', always=True)
    def check_trigger_price_for_sl(cls, v, values):
        if values.get('order_type') in ('SL', 'SL-M') and v is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')
        if values.get('order_type') not in ('SL', 'SL-M') and v is not None:
             # Allow trigger_price for other types if API permits, otherwise raise ValueError
            pass
        return v

    @validator('validity_ttl', always=True)
    def check_validity_ttl(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if values.get('validity') != 'TTL' and v is not None:
            raise ValueError('validity_ttl is only applicable for TTL validity')
        return v

    @validator('iceberg_legs', 'iceberg_quantity', always=True)
    def check_iceberg_params(cls, v, values, field):
        is_iceberg = values.get('variety') == 'iceberg'
        if is_iceberg and field.name == 'iceberg_legs' and (v is None or not (2 <= v <= 10)):
            raise ValueError('iceberg_legs must be between 2 and 10 for iceberg orders')
        if is_iceberg and field.name == 'iceberg_quantity' and v is None:
            raise ValueError('iceberg_quantity is required for iceberg orders')
        if not is_iceberg and v is not None:
            raise ValueError(f'{field.name} is only applicable for iceberg variety')
        return v

    @validator('auction_number', always=True)
    def check_auction_number(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction variety')
        if values.get('variety') != 'auction' and v is not None:
            raise ValueError('auction_number is only applicable for auction variety')
        return v

class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order."""
    variety: Literal['regular', 'co', 'amo', 'iceberg'] = Field(..., description="Order variety to modify.")
    order_id: str = Field(..., description="The unique order ID to modify.")
    parent_order_id: Optional[str] = Field(None, description="Parent order id for second leg CO modification.")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (Regular orders only).")
    quantity: Optional[int] = Field(None, gt=0, description="New quantity (Regular orders only).")
    price: Optional[float] = Field(None, description="New price (Regular LIMIT, CO LIMIT orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (Regular SL/SL-M, CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (Regular orders only).")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field(None, description="New validity (Regular orders only).")

    @validator('order_type', 'quantity', 'disclosed_quantity', 'validity', always=True)
    def check_regular_only_fields(cls, v, values, field):
        # These fields are typically only modifiable for 'regular' variety according to docs/common practice
        # Adjust validation based on exact API capabilities if needed
        if values.get('variety') != 'regular' and v is not None:
            # Log a warning or raise error if strict validation is desired
            # print(f"Warning: Field '{field.name}' might only be applicable for 'regular' variety.")
            pass # Allow modification attempt, let API handle validity
        return v

    @validator('parent_order_id', always=True)
    def check_parent_order_id(cls, v, values):
        if values.get('variety') == 'co' and v is None:
            # Parent ID might be needed for second leg CO mods, depends on API specifics
            pass # Assume optional unless API strictly requires it
        if values.get('variety') != 'co' and v is not None:
            raise ValueError("parent_order_id is only applicable for CO variety modifications")
        return v

class CancelOrderParams(BaseModel):
    """Parameters for cancelling an order."""
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety to cancel.")
    order_id: str = Field(..., description="The unique order ID to cancel.")
    parent_order_id: Optional[str] = Field(None, description="Parent order id for second leg CO cancellation.")

    @validator('parent_order_id', always=True)
    def check_parent_order_id(cls, v, values):
        if values.get('variety') != 'co' and v is not None:
            raise ValueError("parent_order_id is only applicable for CO variety cancellations")
        return v

# --- Output Models ---

class OrderIdResponseData(BaseModel):
    order_id: str = Field(..., description="The unique order ID assigned by Kite Connect.")

class OrderIdResponse(BaseModel):
    """Standard response containing the order ID."""
    # Kite API often wraps the response in {'status': 'success', 'data': {...}}
    # This model directly represents the 'data' part for successful operations.
    order_id: str = Field(..., description="The unique order ID assigned or affected.")

class KiteApiResponse(BaseModel):
    """Generic structure for Kite API responses."""
    status: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error_type: Optional[str] = None
