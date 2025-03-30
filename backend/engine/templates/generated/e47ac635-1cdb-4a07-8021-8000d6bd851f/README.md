# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the order placement and modification endpoints of the Zerodha Kite Connect v3 API. It allows language models or other applications to manage trading orders through a standardized interface.

Built using [FastMCP](https://github.com/your-repo/fastmcp). <!-- Replace with actual FastMCP link if available -->

## Features

*   Place various types of orders (regular, AMO, CO, Iceberg, Auction).
*   Modify existing pending orders.
*   Uses Pydantic for robust request validation.
*   Asynchronous API client built with `httpx`.
*   Handles common Kite Connect API errors.
*   Configurable via environment variables.

## Prerequisites

*   Python 3.8+
*   A Zerodha Kite Connect API key and secret.
*   A valid `access_token` obtained through the Kite Connect login flow. **Note:** Access tokens are typically valid for only one day. You will need a mechanism to generate/refresh this token daily and update the environment variable or `.env` file.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd kite-connect-mcp
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

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory by copying the example file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Kite Connect API key and a valid access token:
    ```dotenv
    # .env
    KITE_API_KEY="your_api_key"
    KITE_ACCESS_TOKEN="your_valid_access_token"
    # KITE_BASE_URL="https://api.kite.trade" # Optional: uncomment to override default
    ```
    **Security Note:** Treat your API key, secret, and access token as sensitive credentials. Do not commit them directly into your version control system.

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will start, typically listening on `http://127.0.0.1:8000` (or as configured by FastMCP).

## Available Tools

The MCP server exposes the following tools:

### 1. `place_order`

Places a new trading order.

*   **Description:** Place an order of a particular variety (regular, amo, co, iceberg, auction).
*   **Input Model:** `PlaceOrderParams` (see `models.py` for details)
    *   `variety`: 'regular', 'amo', 'co', 'iceberg', 'auction'
    *   `tradingsymbol`: e.g., "INFY", "NIFTY23JUL18000CE"
    *   `exchange`: 'NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'
    *   `transaction_type`: 'BUY', 'SELL'
    *   `order_type`: 'MARKET', 'LIMIT', 'SL', 'SL-M'
    *   `quantity`: Positive integer
    *   `product`: 'CNC', 'NRML', 'MIS', 'MTF'
    *   `price`: Float (Required for LIMIT orders)
    *   `trigger_price`: Float (Required for SL, SL-M orders)
    *   `disclosed_quantity`: Optional positive integer
    *   `validity`: 'DAY', 'IOC', 'TTL'
    *   `validity_ttl`: Optional positive integer (Required for TTL validity)
    *   `iceberg_legs`: Optional integer (2-10, Required for 'iceberg' variety)
    *   `iceberg_quantity`: Optional positive integer (Required for 'iceberg' variety)
    *   `auction_number`: Optional string (Required for 'auction' variety)
    *   `tag`: Optional string (max 20 chars)
*   **Returns:** `Dict[str, str]` containing `{"order_id": "<the_new_order_id>"}` on success, or an `ErrorResponse` dictionary on failure.

### 2. `modify_order`

Modifies an existing pending order.

*   **Description:** Modify an open or pending regular order.
*   **Input Model:** `ModifyOrderParams` (see `models.py` for details)
    *   `variety`: 'regular', 'co', 'amo', 'iceberg', 'auction' (Must match the original order's variety)
    *   `order_id`: The ID of the order to modify.
    *   `order_type`: Optional new order type ('MARKET', 'LIMIT', 'SL', 'SL-M')
    *   `quantity`: Optional new positive integer quantity.
    *   `price`: Optional new float price (for LIMIT orders).
    *   `trigger_price`: Optional new float trigger price (for SL, SL-M orders).
    *   `disclosed_quantity`: Optional new positive integer disclosed quantity.
    *   `validity`: Optional new validity ('DAY', 'IOC', 'TTL').
*   **Returns:** `Dict[str, str]` containing `{"order_id": "<the_modified_order_id>"}` on success, or an `ErrorResponse` dictionary on failure.

## Error Handling

The API client (`client.py`) attempts to catch common errors:

*   `AuthenticationError`: Invalid API key or access token (HTTP 403).
*   `InputValidationError`: Invalid parameters sent to the API (HTTP 400).
*   `OrderRejectionError`: Order rejected due to margins, validation rules, etc. (often HTTP 400).
*   `NetworkError`: Could not connect to the Kite API.
*   `TimeoutError`: Request timed out.
*   `KiteConnectError`: Other generic API errors.

The MCP tools return an `ErrorResponse` dictionary in case of failure, containing `error_type`, `message`, and `code`.

## Rate Limiting

The Kite Connect API has rate limits (typically 10 requests per second). This client implementation *does not* actively enforce rate limiting. For high-throughput applications, consider adding a rate-limiting library like `asyncio-throttle` or `limits`.
