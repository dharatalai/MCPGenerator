# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the order management functionalities of the Zerodha Kite Connect V3 API. It allows language models or other applications to place, modify, and cancel trading orders through a standardized MCP interface.

## Features

*   Provides MCP tools for:
    *   Placing new orders (`place_order`)
    *   Modifying existing pending orders (`modify_order`)
    *   Cancelling existing pending orders (`cancel_order`)
*   Built using `FastMCP`.
*   Asynchronous API client using `httpx`.
*   Input validation using `Pydantic`.
*   Handles authentication using Kite Connect API Key and Access Token.
*   Structured error handling and logging.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Kite Connect API credentials:
        *   `KITE_API_KEY`: Your application's API key.
        *   `KITE_ACCESS_TOKEN`: The access token obtained after a successful Kite Connect login flow. **Note:** This token is usually valid only for the day it's generated and needs to be updated daily.
        *   `KITE_BASE_URL`: (Optional) Defaults to `https://api.kite.trade`.

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will start, usually on `http://127.0.0.1:8000` (or the default FastMCP port), and log its status.

## Available Tools

The following tools are exposed by the MCP server:

1.  **`place_order`**
    *   **Description:** Place an order of a particular variety (regular, amo, co, iceberg, auction).
    *   **Parameters:**
        *   `variety` (Literal['regular', 'amo', 'co', 'iceberg', 'auction']): Order variety type. (Required)
        *   `tradingsymbol` (str): Tradingsymbol of the instrument. (Required)
        *   `exchange` (Literal['NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX']): Name of the exchange. (Required)
        *   `transaction_type` (Literal['BUY', 'SELL']): Transaction type. (Required)
        *   `order_type` (Literal['MARKET', 'LIMIT', 'SL', 'SL-M']): Order type. (Required)
        *   `quantity` (int): Quantity to transact. (Required)
        *   `product` (Literal['CNC', 'NRML', 'MIS', 'MTF']): Product type. (Required)
        *   `validity` (Literal['DAY', 'IOC', 'TTL']): Order validity. (Required)
        *   `price` (Optional[float]): The price for LIMIT orders.
        *   `trigger_price` (Optional[float]): The trigger price for SL, SL-M orders.
        *   `disclosed_quantity` (Optional[int]): Quantity to disclose publicly (for equity trades).
        *   `validity_ttl` (Optional[int]): Order life span in minutes for TTL validity orders.
        *   `iceberg_legs` (Optional[int]): Total number of legs for iceberg order type (2-10).
        *   `iceberg_quantity` (Optional[int]): Split quantity for each iceberg leg order.
        *   `auction_number` (Optional[str]): A unique identifier for a particular auction.
        *   `tag` (Optional[str]): Optional tag for the order (alphanumeric, max 20 chars).
    *   **Returns:** `Dict` containing `{"order_id": "..."}` on success, or an error dictionary.

2.  **`modify_order`**
    *   **Description:** Modify an open or pending order. Parameters depend on the order variety.
    *   **Parameters:**
        *   `variety` (Literal['regular', 'co', 'amo', 'iceberg', 'auction']): Order variety type being modified. (Required)
        *   `order_id` (str): The ID of the order to modify. (Required)
        *   `order_type` (Optional[Literal['MARKET', 'LIMIT', 'SL', 'SL-M']]): New order type (regular variety).
        *   `quantity` (Optional[int]): New quantity (regular variety).
        *   `price` (Optional[float]): New price (for LIMIT orders, regular/CO).
        *   `trigger_price` (Optional[float]): New trigger price (for SL, SL-M, LIMIT CO orders).
        *   `disclosed_quantity` (Optional[int]): New disclosed quantity (regular variety).
        *   `validity` (Optional[Literal['DAY', 'IOC', 'TTL']]): New validity (regular variety).
    *   **Returns:** `Dict` containing `{"order_id": "..."}` on success, or an error dictionary.

3.  **`cancel_order`**
    *   **Description:** Cancel an open or pending order.
    *   **Parameters:**
        *   `variety` (Literal['regular', 'amo', 'co', 'iceberg', 'auction']): Order variety type being cancelled. (Required)
        *   `order_id` (str): The ID of the order to cancel. (Required)
    *   **Returns:** `Dict` containing `{"order_id": "..."}` on success, or an error dictionary.

## Error Handling

The API client maps common HTTP status codes and potential Kite Connect error messages to specific Python exceptions (defined in `models.py`, e.g., `AuthenticationError`, `InvalidInputError`, `RateLimitError`, `OrderNotFoundError`).

The MCP tools catch these exceptions and return a structured JSON error response:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": "Optional details from the API"
}
```

Check the server logs for detailed error information.

## Important Notes

*   **Access Token:** The Kite Connect `access_token` is short-lived (usually valid for one day). You need a mechanism to generate and update this token in the `.env` file or environment variables daily before starting the server.
*   **Rate Limits:** The Kite Connect API has rate limits (e.g., 10 requests/second for orders). The server will return a `RateLimitError` if these are exceeded, but it does not implement client-side rate limiting.
*   **Disclaimer:** Trading involves risks. Use this software responsibly and test thoroughly in a simulated environment if possible before using it with real funds.
