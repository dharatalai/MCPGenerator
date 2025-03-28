# Zerodha Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect Orders API. It allows AI agents or other applications to manage trading orders (place, modify, cancel) and retrieve order information using a standardized tool interface.

This server is built using [FastMCP](https://github.com/your-repo/fastmcp). <!-- Replace with actual FastMCP link if available -->

## Features

*   Place various types of orders (Regular, AMO, CO, Iceberg, Auction).
*   Modify pending orders.
*   Cancel pending orders.
*   Retrieve the daily order book.
*   Retrieve the history/details of a specific order.
*   Asynchronous API client using `httpx`.
*   Typed inputs and outputs using Pydantic.
*   Configuration via environment variables.
*   Basic error handling for API and network issues.

## Prerequisites

*   Python 3.8+
*   Pip (Python package installer)
*   A Zerodha Kite Connect API Key and Secret.
*   A mechanism to generate a daily `access_token` (This server *requires* a valid `access_token` but does not handle the login flow to generate it. You need to obtain this token separately each day).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
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
        KITE_API_KEY="YOUR_ACTUAL_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_VALID_DAILY_ACCESS_TOKEN"
        KITE_BASE_URL="https://api.kite.trade" # Optional: Keep default unless needed
        ```
    *   **Important:** The `KITE_ACCESS_TOKEN` expires daily. You must update this value with a fresh token obtained through the Kite Connect login flow for the server to function correctly.

## Running the Server

Once configured, you can run the MCP server:

```bash
python main.py
```

The server will start, typically on `http://127.0.0.1:8000` (or as configured by FastMCP defaults).

## Available Tools

The following tools are exposed by this MCP server:

1.  **`place_order`**: Place a new order.
    *   Input: `PlaceOrderParams` model (includes variety, tradingsymbol, exchange, transaction_type, order_type, quantity, product, etc.)
    *   Returns: `PlaceOrderResponse` model (contains `order_id`)

2.  **`modify_order`**: Modify an existing pending order.
    *   Input: `ModifyOrderParams` model (includes variety, order_id, and fields to modify like quantity, price, trigger_price)
    *   Returns: `ModifyOrderResponse` model (contains `order_id`)

3.  **`cancel_order`**: Cancel an existing pending order.
    *   Input: `CancelOrderParams` model (includes variety, order_id, optional parent_order_id)
    *   Returns: `CancelOrderResponse` model (contains `order_id`)

4.  **`get_orders`**: Retrieve all orders for the current trading day.
    *   Input: None
    *   Returns: `List[Order]` model (list of order details)

5.  **`get_order_history`**: Retrieve the history/details for a specific order.
    *   Input: `GetOrderHistoryParams` model (includes `order_id`)
    *   Returns: `List[OrderHistoryEntry]` model (list of order states/updates)

Refer to `models.py` for detailed definitions of the input and output Pydantic models.

## Error Handling

The server attempts to catch common errors:

*   **API Errors:** Errors returned by the Kite Connect API (e.g., insufficient funds, invalid parameters, token errors) are caught and returned as JSON with an `error` message and `details`.
*   **HTTP Errors:** Network issues or non-2xx responses from the API server are caught.
*   **Validation Errors:** Invalid input parameters according to the Pydantic models will be rejected by FastMCP.
*   **Configuration Errors:** Missing API key or access token will prevent the server from making successful calls (logged on startup).

## Authentication

Authentication with the Kite Connect API is handled via the `api_key` and `access_token` provided in the environment variables. Ensure the `access_token` is valid and refreshed daily.

## Rate Limits

Be mindful of Kite Connect API rate limits (e.g., 3 requests/second for order placement/modification/cancellation, 10 requests/second for data retrieval). This MCP server does not implement client-side rate limiting; exceeding the limits will result in errors from the Kite API.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Use it at your own risk. Ensure you understand the Kite Connect API documentation and the implications of automated trading before use.
