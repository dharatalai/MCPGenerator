# Kite Connect MCP Server

This project implements a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect API. It allows language models or other applications to manage trading orders (place, modify, cancel) and retrieve order history using a standardized MCP interface.

## Features

*   Place new orders (regular, AMO, CO, Iceberg, Auction).
*   Modify existing pending orders.
*   Cancel existing pending orders.
*   Retrieve the list of all orders for the day.
*   Built using FastMCP for efficient serving.
*   Asynchronous API client (`httpx`) for non-blocking operations.
*   Pydantic models for request/response validation.
*   Environment variable based configuration.
*   Basic error handling for API and network issues.

## Prerequisites

*   Python 3.8+
*   A Zerodha Kite Connect API key and secret.
*   A valid `access_token` obtained through the Kite Connect login flow. This token usually has daily validity.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Kite Connect `API_KEY` and a valid `ACCESS_TOKEN`:
        ```dotenv
        KITE_API_KEY="YOUR_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_VALID_ACCESS_TOKEN"
        # Optional: KITE_BASE_URL="https://api.kite.trade"
        ```
    *   **Important:** The `ACCESS_TOKEN` needs to be periodically refreshed as it expires. This server assumes a valid token is provided at startup.

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will start, typically listening on `http://127.0.0.1:8000` (or the configured host/port for FastMCP).

## Available Tools

The following tools are exposed via the MCP server:

1.  **`place_order`**
    *   Description: Place an order of a particular variety.
    *   Input (`PlaceOrderParams` model):
        *   `variety` (required): 'regular', 'amo', 'co', 'iceberg', 'auction'
        *   `tradingsymbol` (required): e.g., "INFY", "NIFTY23JULFUT"
        *   `exchange` (required): 'NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'
        *   `transaction_type` (required): 'BUY', 'SELL'
        *   `order_type` (required): 'MARKET', 'LIMIT', 'SL', 'SL-M'
        *   `quantity` (required): Positive integer
        *   `product` (required): 'CNC', 'NRML', 'MIS', 'MTF'
        *   `price` (optional): Float, required for 'LIMIT' orders.
        *   `trigger_price` (optional): Float, required for 'SL', 'SL-M', 'CO' orders.
        *   `disclosed_quantity` (optional): Integer
        *   `validity` (required): 'DAY', 'IOC', 'TTL'
        *   `validity_ttl` (optional): Integer (minutes), required if validity is 'TTL'.
        *   `iceberg_legs` (optional): Integer (2-10), required for 'iceberg' variety.
        *   `iceberg_quantity` (optional): Integer, required for 'iceberg' variety.
        *   `auction_number` (optional): String, required for 'auction' variety.
        *   `tag` (optional): String (max 20 chars).
    *   Returns: `{"order_id": "<string>"}` on success, or `{"error": "..."}` on failure.

2.  **`modify_order`**
    *   Description: Modify an open or pending order.
    *   Input (`ModifyOrderParams` model):
        *   `variety` (required): 'regular', 'co', 'amo', 'iceberg'
        *   `order_id` (required): The ID of the order to modify.
        *   `parent_order_id` (optional): String, required for modifying second leg of CO.
        *   `order_type` (optional): New order type ('MARKET', 'LIMIT', 'SL', 'SL-M').
        *   `quantity` (optional): New quantity (positive integer).
        *   `price` (optional): New price (float, for LIMIT).
        *   `trigger_price` (optional): New trigger price (float, for SL, SL-M, CO).
        *   `disclosed_quantity` (optional): New disclosed quantity (integer).
        *   `validity` (optional): New validity ('DAY', 'IOC', 'TTL').
    *   Returns: `{"order_id": "<string>"}` on success, or `{"error": "..."}` on failure.

3.  **`cancel_order`**
    *   Description: Cancel an open or pending order.
    *   Input (`CancelOrderParams` model):
        *   `variety` (required): 'regular', 'co', 'amo', 'iceberg', 'auction'
        *   `order_id` (required): The ID of the order to cancel.
        *   `parent_order_id` (optional): String, required for cancelling second leg of CO.
    *   Returns: `{"order_id": "<string>"}` on success, or `{"error": "..."}` on failure.

4.  **`get_orders`**
    *   Description: Retrieve the list of all orders (open, pending, and executed) for the day.
    *   Input (`GetOrdersParams` model): None required.
    *   Returns: `{"orders": [Order, Order, ...]}` where `Order` is a dictionary containing detailed order information (see `models.py/Order` for fields), or `{"error": "..."}` on failure.

## Error Handling

The server attempts to catch common errors:

*   **Authentication Errors:** If the `API_KEY` or `ACCESS_TOKEN` is invalid or expired (HTTP 401/403).
*   **Validation Errors:** If the input parameters are incorrect (HTTP 400 or Pydantic validation errors).
*   **Not Found Errors:** If an `order_id` doesn't exist (HTTP 404).
*   **Rate Limit Errors:** If the Kite API rate limits are exceeded (HTTP 429).
*   **Network Errors:** If the server cannot reach the Kite API.
*   **API Errors:** Specific errors returned by the Kite API (e.g., insufficient funds, RMS rejection).

Errors are returned as a JSON dictionary with an `"error"` key containing a descriptive message, and potentially `"status_code"` and `"details"` keys.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Use it at your own risk. Ensure you understand the Kite Connect API documentation and the implications of automated trading before use.
