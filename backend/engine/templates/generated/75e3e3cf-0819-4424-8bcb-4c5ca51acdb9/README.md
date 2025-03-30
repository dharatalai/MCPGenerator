# KiteConnectOrders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect API v3, specifically focusing on order management operations.

It allows language models or other applications to place, modify, cancel, and retrieve trading orders via a standardized MCP interface, leveraging the FastMCP framework.

## Features

*   Place new orders (regular, AMO, CO, Iceberg, Auction).
*   Modify existing pending orders.
*   Cancel pending orders.
*   Retrieve a list of all orders for the current trading day.
*   Retrieve the history/updates for a specific order.
*   Built with FastMCP for easy integration.
*   Asynchronous API client using `httpx`.
*   Typed requests and responses using Pydantic.
*   Environment variable-based configuration for API keys.
*   Basic error handling for API and network issues.

## Prerequisites

*   Python 3.8+
*   Zerodha Kite Developer Account and API Key.
*   A valid `access_token` (obtained via the Kite Connect login flow - this token is typically valid for one trading day).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
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
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Kite API Key and a valid Access Token:
    ```
    KITE_API_KEY=your_api_key
    KITE_ACCESS_TOKEN=your_valid_access_token
    # KITE_BASE_URL=https://api.kite.trade # Optional: Uncomment to override default
    ```
    **Important:** The `KITE_ACCESS_TOKEN` needs to be generated daily through the Kite Connect login flow. This MCP server does *not* handle the login flow itself; it assumes a valid token is provided.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
# For development with auto-reload
uvicorn main:mcp.app --reload --host 0.0.0.0 --port 8000

# For production
uvicorn main:mcp.app --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000` (or the specified host/port).

## Available Tools

The following tools are exposed via the MCP server:

1.  **`place_order`**
    *   Description: Place an order of a particular variety.
    *   Input: `PlaceOrderParams` model (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, etc.)
    *   Returns: `Dict[str, str]` containing `order_id` on success, or `ErrorResponse` on failure.

2.  **`modify_order`**
    *   Description: Modify attributes of a pending regular or cover order.
    *   Input: `ModifyOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, `trigger_price`, etc.)
    *   Returns: `Dict[str, str]` containing `order_id` on success, or `ErrorResponse` on failure.

3.  **`cancel_order`**
    *   Description: Cancel a pending order.
    *   Input: `CancelOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `parent_order_id`)
    *   Returns: `Dict[str, str]` containing `order_id` on success, or `ErrorResponse` on failure.

4.  **`get_orders`**
    *   Description: Retrieve the list of all orders for the current trading day.
    *   Input: None
    *   Returns: `Dict[str, List[OrderDetails]]` containing a list of orders under the `orders` key, or `ErrorResponse` on failure.

5.  **`get_order_history`**
    *   Description: Retrieve the history (various stages/updates) of a given order.
    *   Input: `GetOrderHistoryParams` model (see `models.py` for `order_id` field)
    *   Returns: `Dict[str, List[OrderHistoryItem]]` containing a list of history items under the `history` key, or `ErrorResponse` on failure.

Refer to `models.py` for detailed definitions of the input parameter models and the structure of response models (`OrderDetails`, `OrderHistoryItem`). Note that response models are based on typical structures and might need adjustments based on the exact Kite API v3 responses.

## Error Handling

The API client (`client.py`) attempts to catch common errors:
*   `httpx.HTTPStatusError`: For 4xx/5xx responses from the Kite API.
*   `httpx.RequestError`: For network issues (DNS resolution, connection errors).
*   Kite API specific errors: If the response JSON indicates an error (`status: 'error'`).

These are wrapped in a custom `KiteApiException` which includes the status code and error type where available. The MCP tools in `main.py` catch these exceptions and return a standardized `ErrorResponse` dictionary.

## Rate Limiting

The Kite Connect API has rate limits (typically around 3 requests per second per API key for order operations). This client does *not* implement client-side rate limiting. If you exceed the limits, the API will return a 429 error, which will be caught and raised as a `KiteApiException`.

## Disclaimer

Trading involves risks. This software is provided "as is" without warranty of any kind. Ensure you understand the Kite Connect API documentation and the risks associated with automated trading before using this tool.
