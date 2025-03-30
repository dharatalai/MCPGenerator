from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict

# Define constants for reusable literals
OrderVariety = Literal['regular', 'amo', 'co', 'iceberg', 'auction']
Exchange = Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']
TransactionType = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT', 'SL', 'SL-M']
ProductType = Literal['CNC', 'NRML', 'MIS', 'MTF']
ValidityType = Literal['DAY', 'IOC', 'TTL']

class PlaceOrderParams(BaseModel):
    """Parameters for placing an order."""
    variety: OrderVariety = Field(..., description="The variety of the order.")
    tradingsymbol: str = Field(..., description="Tradingsymbol of the instrument (e.g., 'INFY', 'NIFTY23JUL17500CE').")
    exchange: Exchange = Field(..., description="Name of the exchange.")
    transaction_type: TransactionType = Field(..., description="Transaction type.")
    order_type: OrderType = Field(..., description="Order type.")
    quantity: int = Field(..., description="Quantity to transact.")
    product: ProductType = Field(..., description="Product type.")
    price: Optional[float] = Field(None, description="The price for LIMIT orders.")
    trigger_price: Optional[float] = Field(None, description="The trigger price for SL, SL-M orders.")
    disclosed_quantity: Optional[int] = Field(None, description="Quantity to disclose publicly (for equity trades).")
    validity: ValidityType = Field(..., description="Order validity.")
    validity_ttl: Optional[int] = Field(None, description="Order life span in minutes for TTL validity orders.")
    iceberg_legs: Optional[int] = Field(None, description="Total number of legs for iceberg order type (2-10). Required if variety is 'iceberg'.")
    iceberg_quantity: Optional[int] = Field(None, description="Split quantity for each iceberg leg order (quantity/iceberg_legs). Required if variety is 'iceberg'.")
    auction_number: Optional[str] = Field(None, description="A unique identifier for a particular auction. Required if variety is 'auction'.")
    tag: Optional[str] = Field(None, description="An optional tag (alphanumeric, max 20 chars) to apply to the order.")

    class Config:
        use_enum_values = True # Ensure literals are passed as strings

class ModifyOrderParams(BaseModel):
    """Parameters for modifying an order."""
    variety: OrderVariety = Field(..., description="The variety of the order being modified.")
    order_id: str = Field(..., description="The ID of the order to modify.")
    parent_order_id: Optional[str] = Field(None, description="Required for modifying second leg of CO orders.")
    order_type: Optional[OrderType] = Field(None, description="New order type (regular variety).")
    quantity: Optional[int] = Field(None, description="New quantity (regular variety).")
    price: Optional[float] = Field(None, description="New price (for LIMIT, CO orders).")
    trigger_price: Optional[float] = Field(None, description="New trigger price (for SL, SL-M, CO orders).")
    disclosed_quantity: Optional[int] = Field(None, description="New disclosed quantity (regular variety).")
    validity: Optional[ValidityType] = Field(None, description="New validity (regular variety).")

    class Config:
        use_enum_values = True # Ensure literals are passed as strings

class OrderResponse(BaseModel):
    """Standard response containing the order ID."""
    order_id: str = Field(..., description="The unique identifier for the order.")

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Description of the error that occurred.")
    details: Optional[Dict] = Field(None, description="Optional details about the error.")
