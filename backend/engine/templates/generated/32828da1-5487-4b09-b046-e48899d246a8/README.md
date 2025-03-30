# KiteConnect Orders MCP Server

This project provides a Model Context Protocol (MCP) server built with FastMCP to interact with the Zerodha Kite Connect Orders API (v3). It allows language models or other clients to manage trading orders (place, modify, cancel, retrieve) through a standardized interface.

## Features

*   Place new orders (Regular, AMO, CO, Iceberg, Auction).
*   Modify existing pending orders.
*   Cancel pending orders.
*   Retrieve the list of all orders for the current trading day.
*   Built with FastMCP for easy integration.
*   Asynchronous API client using `httpx`.
*   Typed inputs and outputs using Pydantic models.
*   Environment variable-based configuration.
*   Basic error handling for API and network issues.

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

## Configuration

This server requires Kite Connect API credentials. You need to obtain an `API Key` and generate an `Access Token`.

1.  **Create a `.env` file:**
    Copy the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Fill in your Kite Connect credentials:
    ```dotenv
    # Kite Connect API Credentials and Configuration
    KITE_API_KEY=YOUR_API_KEY
    KITE_ACCESS_TOKEN=YOUR_GENERATED_ACCESS_TOKEN
    # KITE_BASE_URL=https://api.kite.trade # Optional: Uncomment to override default URL
    ```

    *   `KITE_API_KEY`: Your application's API key from the Kite Developer console.
    *   `KITE_ACCESS_TOKEN`: A valid access token obtained through the Kite Connect login flow. **Note:** Access tokens are short-lived and need to be regenerated periodically (typically daily). This server assumes a valid token is provided. You might need a separate mechanism to refresh this token.

## Running the Server

Once configured, start the MCP server:

```bash
python main.py
```

The server will start, usually on `http://127.0.0.1:8000` (or the default FastMCP port), and log its status.

## Available Tools

The following tools are exposed by this MCP server:

1.  **`place_order`**
    *   **Description:** Place an order of a particular variety (regular, amo, co, iceberg, auction).
    *   **Input:** `PlaceOrderInput` model (includes variety, tradingsymbol, exchange, transaction_type, order_type, quantity, product, validity, and optional fields like price, trigger_price, etc.). See `models.py` for details.
    *   **Output:** `PlaceOrderResponse` model containing the `order_id` on success, or an error dictionary.

2.  **`modify_order`**
    *   **Description:** Modify an open or pending order. Send only the parameters that need to be modified.
    *   **Input:** `ModifyOrderInput` model (includes variety, order_id, and optional fields like parent_order_id, order_type, quantity, price, trigger_price, etc.). See `models.py` for details.
    *   **Output:** `ModifyOrderResponse` model containing the `order_id` on success, or an error dictionary.

3.  **`cancel_order`**
    *   **Description:** Cancel an open or pending order.
    *   **Input:** `CancelOrderInput` model (includes variety, order_id, and optional parent_order_id). See `models.py` for details.
    *   **Output:** `CancelOrderResponse` model containing the `order_id` on success, or an error dictionary.

4.  **`get_orders`**
    *   **Description:** Retrieve the list of all orders (open, pending, executed) for the current trading day.
    *   **Input:** `GetOrdersInput` model (currently takes no parameters).
    *   **Output:** A dictionary containing a list of `OrderDetails` under the key `"orders"`, or an error dictionary.

## Error Handling

The server attempts to catch common errors:

*   **Kite API Errors:** Errors returned by the Kite API (e.g., insufficient funds, invalid parameters) are caught and returned with an `error` type and details.
*   **HTTP Errors:** Standard HTTP errors (4xx, 5xx) during API calls are caught.
*   **Network Errors:** Errors related to network connectivity or timeouts are caught.
*   **Configuration Errors:** Logs an error if API credentials are missing.

Error responses are typically returned as a JSON dictionary with an `"error"` key and often a `"details"` key.
