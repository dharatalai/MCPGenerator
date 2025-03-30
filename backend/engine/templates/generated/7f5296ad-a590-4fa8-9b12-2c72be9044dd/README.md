# KiteConnectMCP Server

This project implements a Model Context Protocol (MCP) server using FastMCP to interact with the Zerodha Kite Connect v3 API. It provides tools for managing trading orders.

## Description

Provides tools to interact with the Kite Connect v3 API for managing trading orders and retrieving trade information. This MCP facilitates placing, modifying, canceling, and retrieving orders and trades.

## Features

*   Place new trading orders (regular, AMO, CO, Iceberg, Auction).
*   Modify existing pending orders.
*   Cancel pending orders.
*   Built with FastMCP for easy integration with AI agents.
*   Asynchronous API client using `httpx`.
*   Pydantic models for type safety and validation.
*   Environment variable based configuration.
*   Basic error handling for API and network issues.

## Available Tools

1.  **`place_order`**: Place an order of a particular variety.
    *   Requires details like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, and optional parameters like `price`, `trigger_price`, etc.
2.  **`modify_order`**: Modify attributes of a pending regular or cover order.
    *   Requires `variety`, `order_id`, and optional new attributes like `quantity`, `price`, `trigger_price`, etc.
3.  **`cancel_order`**: Cancel a pending order.
    *   Requires `variety`, `order_id`, and optionally `parent_order_id` for CO second leg cancellation.

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
        *   `KITE_ACCESS_TOKEN`: A valid access token obtained after user authentication via Kite Connect. **Note:** Access tokens are short-lived and need to be regenerated periodically.
        *   `KITE_BASE_URL` (Optional): Defaults to `https://api.kite.trade` if not set.

    *   **Obtaining Credentials:** You need to register an app on the [Kite Developer Console](https://developers.kite.trade/) to get an `API Key`. The `access_token` is generated dynamically after a user successfully logs in through the Kite Connect login flow. Implementing the full login flow is outside the scope of this MCP server; you need to obtain a valid `access_token` through other means (e.g., using Kite's official libraries or a separate authentication script) and provide it in the `.env` file.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--reload`: Enables auto-reloading when code changes (useful for development).
*   The server will be available at `http://localhost:8000`.
*   The MCP specification will be available at `http://localhost:8000/openapi.json`.
*   Interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.

## Error Handling

The server attempts to catch common errors:
*   **Configuration Errors:** Missing API key or access token.
*   **API Errors:** Errors returned by the Kite Connect API (e.g., invalid parameters, insufficient funds, authentication failure, rate limits) are wrapped in a `KiteConnectError` and returned as an `ErrorResponse` JSON.
*   **Network Errors:** Timeouts or connection issues during API calls.
*   **Validation Errors:** Incorrect input parameters passed to the tools (handled by Pydantic).

Error responses follow the `ErrorResponse` model structure defined in `models.py`.

## Rate Limits

The Kite Connect API has rate limits (e.g., 3 requests per second for order placement/modification/cancellation). This client does *not* implement client-side rate limiting. Be mindful of these limits when calling the tools frequently to avoid `429 Too Many Requests` errors from the API.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Use it at your own risk and ensure thorough testing before deploying in a live trading environment.
