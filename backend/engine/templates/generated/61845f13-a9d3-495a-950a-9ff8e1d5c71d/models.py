from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict, Any

# --- Input Parameter Models ---

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety type.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument.")
    exchange: Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'] = Field(..., description="Name of the exchange.")
    transaction_type: Literal['BUY', 'SELL'] = Field(..., description="Transaction type.")
    order_type: Literal['MARKET', 'LIMIT', 'SL', 'SL-M'] = Field(..., description="Order type.")
    quantity: int = Field(..., description="Quantity to transact.", gt=0)
    product: Literal['CNC', 'NRML', 'MIS', 'MTF'] = Field(..., description="Product type.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: Literal['DAY', 'IOC', 'TTL'] = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10).", ge=2, le=10)
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction.")
    tag: Optional[str] = Field(None, description="Optional tag for the order (alphanumeric, max 20 chars).", max_length=20)

    @validator('price')
    def check_price_for_limit_order(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') != 'LIMIT' and v is not None:
             # Kite API might ignore it, but good practice to validate
             pass # Or raise ValueError('Price is only applicable for LIMIT orders')
        return v

    @validator('trigger_price')
    def check_trigger_price_for_sl_orders(cls, v, values):
        if values.get('order_type') in ['SL', 'SL-M'] and v is None:
            raise ValueError('Trigger price is required for SL/SL-M orders')
        if values.get('order_type') not in ['SL', 'SL-M'] and v is not None:
            # Or raise ValueError('Trigger price is only applicable for SL/SL-M orders')
            pass
        return v

    @validator('validity_ttl')
    def check_validity_ttl_for_ttl_validity(cls, v, values):
        if values.get('validity') == 'TTL' and v is None:
            raise ValueError('validity_ttl is required for TTL validity')
        if values.get('validity') != 'TTL' and v is not None:
            raise ValueError('validity_ttl is only applicable for TTL validity')
        return v

    @validator('iceberg_legs', 'iceberg_quantity')
    def check_iceberg_params(cls, v, values, field):
        if values.get('variety') == 'iceberg':
            if field.name == 'iceberg_legs' and v is None:
                raise ValueError('iceberg_legs is required for iceberg orders')
            if field.name == 'iceberg_quantity' and v is None:
                raise ValueError('iceberg_quantity is required for iceberg orders')
        elif v is not None:
            raise ValueError(f'{field.name} is only applicable for iceberg orders')
        return v

    @validator('auction_number')
    def check_auction_number(cls, v, values):
        if values.get('variety') == 'auction' and v is None:
            raise ValueError('auction_number is required for auction orders')
        if values.get('variety') != 'auction' and v is not None:
            raise ValueError('auction_number is only applicable for auction orders')
        return v

class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order."""
    variety: Literal['regular', 'co', 'amo', 'iceberg', 'auction'] = Field(..., description="Order variety type being modified.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    order_type: Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']] = Field(None, description="New order type (regular variety).")
    quantity: Optional[int] = Field(None, description="New quantity (regular variety).", gt=0)
    price: Optional[float] = Field(None, description="New price (for LIMIT orders, regular/CO).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, LIMIT CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (regular variety).")
    validity: Optional[Literal['DAY', 'IOC', 'TTL']] = Field(None, description="New validity (regular variety).")

    # Add validators similar to PlaceOrderParams if needed for modification logic
    # e.g., ensuring price is provided if changing order_type to LIMIT

class CancelOrderParams(BaseModel):
    """Parameters for cancelling an order."""
    variety: Literal['regular', 'amo', 'co', 'iceberg', 'auction'] = Field(..., description="Order variety type being cancelled.")
    order_id: str = Field(..., description="The ID of the order to cancel.")

# --- Response Models ---

class OrderResponse(BaseModel):
    """Standard response containing the order ID."""
    order_id: str = Field(..., description="The unique ID of the order.")

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="The type of error that occurred.")
    message: Optional[str] = Field(None, description="A human-readable message explaining the error.")
    details: Optional[Any] = Field(None, description="Additional details about the error, potentially from the API.")

# --- Custom Exceptions ---

class KiteConnectError(Exception):
    """Base exception for all Kite Connect API errors."""
    def __init__(self, message="An API error occurred", status_code=None, details=None):
        self.message = message
        self.status_code = status_code
        self.details = details # Store raw error response if available
        super().__init__(self.message)

class AuthenticationError(KiteConnectError):
    """Raised for authentication failures (403 Forbidden)."""
    def __init__(self, message="Authentication failed. Check API key and access token.", details=None):
        super().__init__(message, status_code=403, details=details)

class InvalidInputError(KiteConnectError):
    """Raised for invalid input parameters (400 Bad Request)."""
    def __init__(self, message="Invalid input provided.", details=None):
        super().__init__(message, status_code=400, details=details)

class InsufficientFundsError(KiteConnectError):
    """Raised when there are insufficient funds (specific error message or code needed)."""
    # Kite specific errors might be in the response body, not just status code
    def __init__(self, message="Insufficient funds for the order.", details=None):
        super().__init__(message, details=details)

class NetworkError(KiteConnectError):
    """Raised for network-related issues (e.g., connection errors, timeouts)."""
    def __init__(self, message="Network error communicating with Kite API.", details=None):
        super().__init__(message, details=details)

class RateLimitError(KiteConnectError):
    """Raised when API rate limits are exceeded (429 Too Many Requests)."""
    def __init__(self, message="API rate limit exceeded.", details=None):
        super().__init__(message, status_code=429, details=details)

class ExchangeError(KiteConnectError):
    """Raised for exchange-specific errors (e.g., market closed, instrument not available)."""
    # Often indicated by specific error messages in the response body (500 or 503 potentially)
    def __init__(self, message="An exchange-related error occurred.", details=None):
        super().__init__(message, details=details)

class OrderPlacementError(KiteConnectError):
    """Generic error during order placement (potentially 500 Internal Server Error or specific message)."""
    def __init__(self, message="Failed to place the order.", details=None):
        super().__init__(message, details=details)

class OrderModificationError(KiteConnectError):
    """Generic error during order modification."""
    def __init__(self, message="Failed to modify the order.", details=None):
        super().__init__(message, details=details)

class OrderCancellationError(KiteConnectError):
    """Generic error during order cancellation."""
    def __init__(self, message="Failed to cancel the order.", details=None):
        super().__init__(message, details=details)

class OrderNotFoundError(KiteConnectError):
    """Raised when trying to modify/cancel an order that doesn't exist (often 404 or specific message)."""
    def __init__(self, message="Order not found.", details=None):
        # Kite might return 400 or other codes for this, check documentation
        super().__init__(message, status_code=404, details=details)

class GeneralError(KiteConnectError):
    """Raised for unexpected server errors (500, 502, 503, 504)."""
    def __init__(self, message="An unexpected server error occurred.", status_code=500, details=None):
        super().__init__(message, status_code=status_code, details=details)
