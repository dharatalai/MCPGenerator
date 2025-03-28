# Zerodha Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server built with FastMCP to interact with the Zerodha Kite Connect v3 API, specifically focusing on order management (placing and modifying orders).

## Description

The server exposes tools that allow language models or other applications to:

*   Place various types of trading orders (Regular, AMO, CO, Iceberg, Auction).
*   Modify attributes of existing pending orders.

It handles communication with the Zerodha API, including authentication, request formatting, and error handling.

## Features

*   **Place Orders:** Supports placing orders with various parameters like symbol, exchange, quantity, price, order type, product type, validity, etc.
*   **Modify Orders:** Allows modification of pending orders (e.g., changing price, quantity, trigger price).
*   **Typed Interfaces:** Uses Pydantic models for clear and validated tool inputs and outputs.
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking I/O.
*   **Error Handling:** Maps Zerodha API errors to specific exceptions and provides informative error responses.
*   **Environment Variable Configuration:** API keys and tokens are configured via environment variables.

## Available Tools

1.  **`place_order`**: Places an order of a particular variety.
    *   **Description:** Places an order (regular, amo, co, iceberg, auction) with specified parameters.
    *   **Inputs:** `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `price` (optional), `trigger_price` (optional), `disclosed_quantity` (optional), `validity` (optional, default: DAY), `validity_ttl` (optional), `iceberg_legs` (optional), `iceberg_quantity` (optional), `auction_number` (optional), `tag` (optional).
    *   **Returns:** A dictionary containing the `order_id` of the successfully placed order or an error response.

2.  **`modify_order`**: Modifies attributes of a pending order.
    *   **Description:** Modifies attributes (quantity, price, trigger price, order type, validity) of a pending regular order. For Cover Orders (CO), only `trigger_price` can be modified.
    *   **Inputs:** `variety`, `order_id`, `parent_order_id` (optional), `order_type` (optional), `quantity` (optional), `price` (optional), `trigger_price` (optional), `disclosed_quantity` (optional), `validity` (optional, must be DAY for regular orders).
    *   **Returns:** A dictionary containing the `order_id` of the successfully modified order or an error response.

## Setup and Installation

1.  **Clone the repository (if applicable):**
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

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Zerodha API Key and a valid Access Token:
        ```dotenv
        ZERODHA_API_KEY="your_actual_api_key"
        ZERODHA_ACCESS_TOKEN="your_valid_access_token"
        # ZERODHA_API_BASE_URL="https://api.kite.trade" # Optional: Uncomment to override default
        ```
    *   **Important:** The `ZERODHA_ACCESS_TOKEN` is short-lived (typically valid for a day) and needs to be obtained through the Kite Connect login flow. You will need to update this token regularly.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
# Default: http://127.0.0.1:8000
uvicorn main:mcp --host 127.0.0.1 --port 8000

# Run with auto-reload for development
uvicorn main:mcp --host 127.0.0.1 --port 8000 --reload
```

The server will start, and you can interact with it using an MCP client or test endpoints (like `/tools` for discovery) via HTTP.

## Authentication

Authentication with the Zerodha Kite Connect API is handled using the `api_key` and `access_token` provided in the `.env` file. These are sent in the `Authorization` header for every API request.

Ensure your `access_token` is valid. If you receive `AuthenticationError` or `TokenException` errors, you likely need to regenerate the access token.

## Error Handling

The server catches common errors:

*   **HTTP Errors:** Handled by `httpx`.
*   **API Errors:** Specific errors returned by the Kite Connect API (e.g., insufficient funds, invalid parameters, authentication issues) are parsed and returned as structured `ErrorResponse` objects.
*   **Network Errors:** Timeouts or connection issues.
*   **Validation Errors:** Issues with the input parameters provided to the tools.

Error responses include a `status`, `message`, and often an `error_type` corresponding to the Kite Connect error type.

## Rate Limiting

The Zerodha Kite Connect API has rate limits (typically 3 requests per second). This client **does not** implement explicit rate limiting logic. If you anticipate high request volumes, you may need to add rate limiting using libraries like `asyncio-throttle` or `aiolimiter` in the `client.py` file to avoid hitting API limits (HTTP 429 errors).
