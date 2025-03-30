# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server built with FastMCP to interact with the Kite Connect v3 API, specifically focusing on order management functionalities.

It allows language models or other clients compatible with MCP to place, modify, cancel, and retrieve trading orders via the Kite platform.

## Features

This MCP server exposes the following tools:

*   **`place_order`**: Places a new trading order (regular, AMO, CO, Iceberg, Auction).
*   **`modify_order`**: Modifies attributes (like price, quantity) of an open or pending order (regular, CO).
*   **`cancel_order`**: Cancels an open or pending order.
*   **`get_orders`**: Retrieves the list of all orders placed during the current trading day.
*   **`get_order_history`**: Retrieves the detailed state transition history for a specific order.

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

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Kite Connect API Key and a valid Access Token:
        ```env
        KITE_API_KEY="YOUR_KITE_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_GENERATED_ACCESS_TOKEN"
        ```
    *   **Important:** You need to obtain an `api_key` from Zerodha Kite Connect and generate an `access_token` using their login flow. The `access_token` is typically valid for one trading day. Refer to the [Kite Connect HTTP API documentation](https://kite.trade/docs/connect/v3/user/) for details on obtaining credentials.

## Running the Server

Use an ASGI server like Uvicorn to run the application:

```bash
uvicorn main:mcp.app --reload --host 0.0.0.0 --port 8000
```

*   `--reload`: Enables auto-reloading when code changes (useful for development).
*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.

The server will start, and you can interact with it using an MCP client.

## API Documentation

Once the server is running, FastAPI automatically generates interactive API documentation.

*   **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
*   **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

These interfaces allow you to explore the available tools, view their schemas (input parameters and expected responses), and even test them directly from your browser.

## Tool Details

Refer to the API documentation (`/docs`) for detailed information on each tool's parameters and expected data structures.

The implementation uses Pydantic models (`models.py`) for strict data validation based on the Kite Connect API documentation.

## Error Handling

The server attempts to catch common errors:

*   **HTTP Errors:** Errors during communication with the Kite API (e.g., 4xx client errors, 5xx server errors).
*   **Kite API Errors:** Specific errors returned by the Kite API (e.g., insufficient funds, validation errors, order rejections, invalid state for modification/cancellation). These are wrapped in a `KiteConnectError` exception and returned as JSON with `error`, `error_type`, and `status_code` fields.
*   **Configuration Errors:** Missing API keys or access tokens.
*   **Unexpected Errors:** Other runtime errors during processing.

Error responses are returned in a JSON format like:
`{"error": "Error message", "error_type": "KiteErrorType", "status_code": 400}`

## Rate Limits

The Kite Connect API imposes rate limits (typically 3 requests per second per user per app). This implementation **does not** include client-side rate limiting. Ensure that your usage patterns respect these limits to avoid being blocked by the API.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Use it at your own risk and ensure thorough testing before deploying in a live trading environment.
