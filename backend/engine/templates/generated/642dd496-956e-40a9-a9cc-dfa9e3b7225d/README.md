# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the order management endpoints of the Zerodha Kite Connect v3 API. It allows language models or other clients to place and modify trading orders through a standardized MCP interface.

## Features

*   **Place Orders:** Place various types of orders (regular, AMO, CO, Iceberg, Auction).
*   **Modify Orders:** Modify pending regular and CO orders.
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking I/O.
*   **Typed:** Uses Pydantic for request validation and data modeling.
*   **Error Handling:** Maps Kite Connect API errors to specific exceptions.
*   **Configurable:** Uses environment variables for API credentials.

## Prerequisites

*   Python 3.8+
*   Zerodha Kite Connect API Key and Access Token.
    *   You need to register an app on the [Kite Developer Console](https://developers.kite.trade/).
    *   You need a valid `access_token` obtained through the Kite Connect login flow. This token usually has a daily expiry and needs to be regenerated.
*   Understanding of Kite Connect API parameters and order types.

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
    *   Edit the `.env` file and add your Kite Connect API Key and a valid Access Token:
        ```dotenv
        KITE_API_KEY="YOUR_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_VALID_ACCESS_TOKEN"
        # KITE_API_BASE_URL="https://api.kite.trade" # Optional: uncomment to override default
        ```
    *   **Important:** The `KITE_ACCESS_TOKEN` is short-lived. You will need a mechanism to refresh this token regularly and update the `.env` file or the environment variable.

## Running the Server

Use `uvicorn` to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 127.0.0.1 --port 8000 --reload
```

*   `--reload`: Enables auto-reloading for development (remove in production).
*   Adjust `--host` and `--port` as needed.

## Available Tools

The MCP server exposes the following tools:

1.  **`place_order`**
    *   **Description:** Place an order of a specified variety (regular, amo, co, iceberg, auction). Returns the order_id upon successful placement.
    *   **Input Model:** `PlaceOrderParams` (see `models.py` for details)
        *   `variety`: 'regular', 'amo', 'co', 'iceberg', 'auction'
        *   `tradingsymbol`: e.g., "INFY"
        *   `exchange`: 'NSE', 'BSE', 'NFO', etc.
        *   `transaction_type`: 'BUY' or 'SELL'
        *   `order_type`: 'MARKET', 'LIMIT', 'SL', 'SL-M'
        *   `quantity`: Integer > 0
        *   `product`: 'CNC', 'NRML', 'MIS', 'MTF'
        *   `price`: Float (Required for LIMIT)
        *   `trigger_price`: Float (Required for SL, SL-M)
        *   `validity`: 'DAY', 'IOC', 'TTL'
        *   ... (see `models.PlaceOrderParams` for all optional fields like `disclosed_quantity`, `validity_ttl`, `iceberg_legs`, `tag`, etc.)
    *   **Returns:** `Dict[str, Any]` - e.g., `{'status': 'success', 'data': {'order_id': '151220000000000'}}` or `{'status': 'error', 'error_type': '...', 'message': '...'}`

2.  **`modify_order`**
    *   **Description:** Modify attributes of a pending regular or cover order (CO).
    *   **Input Model:** `ModifyOrderParams` (see `models.py` for details)
        *   `variety`: 'regular' or 'co'
        *   `order_id`: The ID of the order to modify.
        *   `order_type`: New order type (Regular only)
        *   `quantity`: New quantity (Regular only)
        *   `price`: New price (LIMIT)
        *   `trigger_price`: New trigger price (SL, SL-M, CO)
        *   `validity`: New validity (Regular only)
        *   ... (see `models.ModifyOrderParams` for optional fields)
    *   **Returns:** `Dict[str, Any]` - e.g., `{'status': 'success', 'data': {'order_id': '151220000000000'}}` or `{'status': 'error', 'error_type': '...', 'message': '...'}`

## Error Handling

The client (`client.py`) attempts to map HTTP errors and Kite Connect specific error responses (based on status codes and response bodies) to custom exceptions (`KiteConnectError` subclasses). These errors are caught in `main.py` and returned as structured JSON error messages.

Common errors include:
*   `AuthenticationError`: Invalid API key or access token (HTTP 403).
*   `OrderPlacementError`/`OrderModificationError`: Invalid parameters, insufficient funds, order not found, etc. (HTTP 400).
*   `RateLimitError`: Exceeding API rate limits (HTTP 429).
*   `NetworkError`: Connection issues or timeouts.
*   `ServerError`: Errors on the Kite Connect API side (HTTP 5xx).

## Rate Limiting

The Kite Connect API enforces rate limits (typically 10 requests/second). This client includes basic retry logic for transient errors (`NetworkError`, `RateLimitError`, `ServerError`) using `tenacity`. However, it does **not** implement proactive rate limiting. If you anticipate high request volumes, consider adding a more robust rate limiting mechanism.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Use it at your own risk. Ensure thorough testing in a simulated environment before using with real funds. The developers are not responsible for any financial losses incurred.
