# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect Orders API (v3). It allows language models or other clients to place, modify, and cancel trading orders through a standardized MCP interface.

## Features

*   Exposes Kite Connect order management functions as MCP tools.
*   Uses `FastMCP` for the server implementation.
*   Asynchronous API client built with `httpx`.
*   Input validation using `Pydantic` models.
*   Handles common Kite Connect API errors.
*   Configurable via environment variables.

## Prerequisites

*   Python 3.8+
*   Zerodha Kite Connect API Key and Secret.
*   A valid `access_token` obtained through the Kite Connect login flow (this token is typically valid for one trading day).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
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
    *   Edit the `.env` file and add your Kite Connect `API_KEY` and a valid `ACCESS_TOKEN`.
        ```dotenv
        KITE_API_KEY="YOUR_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_ACCESS_TOKEN"
        # KITE_BASE_URL="https://api.kite.trade" # Optional: uncomment to override default
        ```
    *   **Important:** The `ACCESS_TOKEN` needs to be generated daily through the Kite Connect login flow.

## Running the Server

Use `uvicorn` to run the MCP server:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--reload`: Enables auto-reloading during development.
*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.

The MCP server will be available at `http://localhost:8000` (or the specified host/port).

## Available MCP Tools

The following tools are exposed by this MCP server:

1.  **`place_order`**
    *   **Description:** Place an order of a particular variety (regular, amo, co, iceberg, auction).
    *   **Input Model:** `PlaceOrderParams` (see `models.py` for details)
        *   `variety`: 'regular', 'amo', 'co', 'iceberg', 'auction'
        *   `tradingsymbol`: e.g., "INFY", "NIFTY23AUGFUT"
        *   `exchange`: 'NSE', 'BSE', 'NFO', 'CDS', 'BCD', 'MCX'
        *   `transaction_type`: 'BUY', 'SELL'
        *   `order_type`: 'MARKET', 'LIMIT', 'SL', 'SL-M'
        *   `quantity`: Integer > 0
        *   `product`: 'CNC', 'NRML', 'MIS', 'MTF'
        *   `price`: Float (Required for LIMIT orders)
        *   `trigger_price`: Float (Required for SL, SL-M orders)
        *   `validity`: 'DAY', 'IOC', 'TTL'
        *   `disclosed_quantity`: Optional[int]
        *   `validity_ttl`: Optional[int] (Required for TTL validity)
        *   `iceberg_legs`: Optional[int] (Required for iceberg variety)
        *   `iceberg_quantity`: Optional[int] (Required for iceberg variety)
        *   `auction_number`: Optional[str] (Required for auction variety)
        *   `tag`: Optional[str] (max 20 chars)
    *   **Returns:** `Dict[str, Any]` containing the API response, typically `{'status': 'success', 'data': {'order_id': '...'}}` or `{'error': '...'}`.

2.  **`modify_order`**
    *   **Description:** Modify an open or pending order.
    *   **Input Model:** `ModifyOrderParams` (see `models.py` for details)
        *   `variety`: 'regular', 'amo', 'co', 'iceberg', 'auction'
        *   `order_id`: The ID of the order to modify.
        *   `parent_order_id`: Optional[str] (Required for second leg CO modification)
        *   `order_type`: Optional[OrderType]
        *   `quantity`: Optional[int]
        *   `price`: Optional[float]
        *   `trigger_price`: Optional[float]
        *   `disclosed_quantity`: Optional[int]
        *   `validity`: Optional[ValidityType]
    *   **Returns:** `Dict[str, Any]` containing the API response, typically `{'status': 'success', 'data': {'order_id': '...'}}` or `{'error': '...'}`.

3.  **`cancel_order`**
    *   **Description:** Cancel an open or pending order.
    *   **Input Model:** `CancelOrderParams` (see `models.py` for details)
        *   `variety`: 'regular', 'amo', 'co', 'iceberg', 'auction'
        *   `order_id`: The ID of the order to cancel.
        *   `parent_order_id`: Optional[str] (Required for second leg CO cancellation)
    *   **Returns:** `Dict[str, Any]` containing the API response, typically `{'status': 'success', 'data': {'order_id': '...'}}` or `{'error': '...'}`.

## Error Handling

The client attempts to map common HTTP status codes and Kite API error messages to specific exceptions (`AuthenticationError`, `ValidationError`, `RateLimitError`, `InsufficientFundsError`, `OrderNotFoundError`, `NetworkError`, `ExchangeError`, `GeneralError`). These are caught by the MCP tools, logged, and returned as an error dictionary: `{"error": "Error message"}`.

## Rate Limits

The Kite Connect API enforces rate limits (e.g., 10 requests per second for order placement/modification). This client implementation does *not* automatically handle rate limiting (e.g., with retries or throttling). If you expect high request volumes, you may need to add rate-limiting logic to the client or the calling application.
