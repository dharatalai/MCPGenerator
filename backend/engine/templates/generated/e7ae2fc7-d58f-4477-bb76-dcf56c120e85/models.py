from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Literal, Dict, Any

# Define constants for reusable literals
VarietyType = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
ExchangeType = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: VarietyType = Field(..., description="Order variety (regular, amo, co, iceberg, auction)")
    exchange: ExchangeType = Field(..., description="Name of the exchange (NSE, BSE, NFO, CDS, BCD, MCX)")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY21JUNFUT')")
    transaction_type: TransactionType = Field(..., description="Transaction type (BUY or SELL)")
    order_type: OrderType = Field(..., description="Order type (MARKET, LIMIT, SL, SL-M)")
    quantity: int = Field(..., description="Quantity to transact (must be positive)")
    product: ProductType = Field(..., description="Product type (CNC, NRML, MIS, MTF)")
    price: Optional[float] = Field(None, description="The price for LIMIT or SL orders. Required for LIMIT/SL, ignored for MARKET/SL-M.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M, or CO orders. Required for SL/SL-M.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades only, must be non-negative)")
    validity: ValidityType = Field("DAY", description="Order validity (DAY, IOC, TTL)")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes. Required if validity is TTL.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order (must be 2-10). Required if variety is iceberg.")
    tag: Optional[str] = Field(None, description="An optional tag for the order. Max 20 chars.") # Added common optional field

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

    @validator('disclosed_quantity')
    def disclosed_quantity_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Disclosed quantity must be non-negative')
        return v

    @root_validator
    def check_conditional_required_fields(cls, values):
        order_type = values.get('order_type')
        price = values.get('price')
        trigger_price = values.get('trigger_price')
        variety = values.get('variety')
        validity = values.get('validity')
        validity_ttl = values.get('validity_ttl')
        iceberg_legs = values.get('iceberg_legs')

        if order_type in ['LIMIT', 'SL'] and price is None:
            raise ValueError('Price is required for LIMIT and SL orders')

        if order_type in ['SL', 'SL-M'] and trigger_price is None:
            raise ValueError('Trigger price is required for SL and SL-M orders')

        if variety == 'co' and trigger_price is None:
             # Note: Kite Connect docs imply trigger_price might be optional for CO depending on context, 
             # but often it's needed or calculated. Adding validation based on common usage.
             # Adjust if specific CO variations don't need it.
             pass # Let's assume API handles CO trigger price logic for now, or adjust validation as needed.

        if validity == 'TTL' and validity_ttl is None:
            raise ValueError('validity_ttl is required when validity is TTL')

        if validity != 'TTL' and validity_ttl is not None:
            raise ValueError('validity_ttl is only applicable when validity is TTL')

        if variety == 'iceberg' and iceberg_legs is None:
            raise ValueError('iceberg_legs is required when variety is iceberg')
        
        if variety == 'iceberg' and iceberg_legs is not None and not (2 <= iceberg_legs <= 10):
            raise ValueError('iceberg_legs must be between 2 and 10')

        if variety != 'iceberg' and iceberg_legs is not None:
            raise ValueError('iceberg_legs is only applicable when variety is iceberg')
            
        # Ensure trigger price logic for SL/SL-M
        if order_type == 'SL':
            transaction_type = values.get('transaction_type')
            if transaction_type == 'BUY' and trigger_price is not None and price is not None and trigger_price >= price:
                raise ValueError('For SL BUY orders, trigger_price must be less than price.')
            if transaction_type == 'SELL' and trigger_price is not None and price is not None and trigger_price <= price:
                raise ValueError('For SL SELL orders, trigger_price must be greater than price.')

        return values

class PlaceOrderResponse(BaseModel):
    """Response after successfully placing an order."""
    order_id: str = Field(..., description="The unique order ID.")

class ErrorResponse(BaseModel):
    """Standard error response structure."""
    status: str = Field(..., description="Status of the response, e.g., 'error'")
    message: str = Field(..., description="Detailed error message")
    error_type: str = Field(..., description="Category of the error, e.g., 'InputException', 'NetworkException'")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional error details if available")
