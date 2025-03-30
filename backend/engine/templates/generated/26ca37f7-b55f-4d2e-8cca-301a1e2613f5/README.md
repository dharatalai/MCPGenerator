# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the order placement and management functionalities of the Zerodha Kite Connect API v3.

It allows language models or other applications to place, modify, and cancel trading orders programmatically via the MCP interface.

**Disclaimer:** Trading involves risk. Ensure you understand the Kite Connect API, the parameters involved, and the risks associated with automated trading before using this software with real funds.

## Features

*   Provides MCP tools for:
    *   `place_order`: Place regular, AMO, CO, Iceberg, and Auction orders.
    *   `modify_order`: Modify pending regular and CO orders.
    *   `cancel_order`: Cancel pending orders of any variety.
*   Uses Pydantic models for clear request parameter validation.
*   Asynchronous API client (`httpx`) for non-blocking requests.
*   Handles authentication using Kite API Key and Access Token.
*   Basic error handling for API and network issues.
*   Configurable via environment variables.

## Prerequisites

*   Python 3.8+
*   A Zerodha Kite account.
*   Kite Developer API credentials (API Key).
*   A valid `access_token` (obtained through the Kite Connect login flow - see [Kite Connect Documentation](https://kite.trade/docs/connect/v3/user/)).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd kiteconnect-mcp-server
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    # venv\\Scripts\\activate
    # On macOS/Linux
    source venv/bin/activate
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
    *   Edit the `.env` file and add your Kite `API_KEY` and a valid `ACCESS_TOKEN`:
        ```dotenv
        KITE_API_KEY="YOUR_ACTUAL_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_GENERATED_ACCESS_TOKEN"
        # Optional: KITE_BASE_URL="https://api.kite.trade"
        ```
    *   **Important:** The `ACCESS_TOKEN` is typically valid for only one day. You will need a mechanism to refresh or regenerate this token regularly for continuous operation.

## Running the Server

Use `uvicorn` to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes (useful for development).

The MCP server will be available at `http://localhost:8000` (or your machine's IP address on port 8000).

## Available Tools

The server exposes the following tools via the MCP protocol:

1.  **`place_order`**
    *   **Description:** Place an order of a particular variety.
    *   **Input:** `PlaceOrderParams` model (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `price`, `trigger_price`, etc.).
    *   **Returns:** Dictionary with `order_id` on success, or an error dictionary.

2.  **`modify_order`**
    *   **Description:** Modify an open/pending regular or CO order.
    *   **Input:** `ModifyOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, `trigger_price`, etc.). Note that only `regular` and `co` varieties are typically modifiable.
    *   **Returns:** Dictionary with `order_id` on success, or an error dictionary.

3.  **`cancel_order`**
    *   **Description:** Cancel an open/pending order.
    *   **Input:** `CancelOrderParams` model (see `models.py` for fields `variety`, `order_id`).
    *   **Returns:** Dictionary with `order_id` on success, or an error dictionary.

## Authentication

The server authenticates with the Kite Connect API using the `KITE_API_KEY` and `KITE_ACCESS_TOKEN` provided in the `.env` file. Ensure these are kept secure and that the `ACCESS_TOKEN` is valid.

## Error Handling

The server attempts to catch common errors:
*   **Configuration Errors:** Missing API key or access token.
*   **Validation Errors:** Incorrect parameters passed to tools (handled by Pydantic).
*   **Kite API Errors:** Errors returned by the Kite Connect API (e.g., insufficient funds, invalid parameters, authentication failure, rate limits) are wrapped in a `KiteConnectError` and returned as an error dictionary in the MCP response.
*   **Network Errors:** Timeouts or connection issues when communicating with the Kite API.

Error responses generally follow the format:
`{"status": "error", "message": "Error description", "details": {...}}`

## Rate Limiting

The Kite Connect API enforces rate limits (typically 10 requests per second per API key). This MCP server **does not implement client-side rate limiting**. It is the responsibility of the application using this MCP server to manage request rates and stay within the API limits to avoid `429 Too Many Requests` errors.

## Disclaimer

This software is provided "as is", without warranty of any kind. The authors or copyright holders are not liable for any claim, damages, or other liability arising from the use of this software, especially concerning financial losses incurred through trading.
