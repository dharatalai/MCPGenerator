# KiteConnect MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect API. It allows language models or other applications to perform trading-related actions like placing, modifying, and cancelling orders, as well as retrieving order history using natural language or structured requests via the MCP interface.

This server uses the official `pykiteconnect` library to communicate with the Kite API.

## Features

*   **Place Orders**: Place various types of orders (regular, AMO, CO, Iceberg, Auction).
*   **Modify Orders**: Modify pending regular or cover orders.
*   **Cancel Orders**: Cancel pending orders.
*   **Get Orders**: Retrieve the list of all orders for the current trading day.
*   Built with **FastMCP** for easy integration.
*   Uses **Pydantic** for robust data validation.
*   Includes **error handling** for common Kite API exceptions.

## Prerequisites

*   Python 3.8+
*   A Zerodha Kite account.
*   Kite Connect API Key and API Secret obtained from the [Kite Developer Console](https://developers.kite.trade/).
*   A valid `access_token`. Generating the `access_token` requires implementing the Kite Connect login flow, which is **outside the scope of this server**. You need to obtain this token beforehand and provide it via environment variables.

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
    Create a `.env` file in the project root directory by copying the example file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Kite API Key and the pre-generated Access Token:
    ```dotenv
    # Zerodha Kite Connect API Credentials
    KITE_API_KEY="YOUR_ACTUAL_API_KEY"
    KITE_ACCESS_TOKEN="YOUR_PREGENERATED_ACCESS_TOKEN"

    # Port for the MCP server (optional, defaults to 8000)
    PORT=8000
    ```
    **Important:** The `KITE_ACCESS_TOKEN` needs to be valid. You usually obtain this daily after completing the login flow.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port (can be changed, ensure it matches `PORT` in `.env` if set).
*   `--reload`: Automatically restarts the server when code changes (useful for development).

The MCP server will be available at `http://localhost:8000` (or the configured host/port).

## Available Tools

The server exposes the following tools via the MCP protocol:

1.  **`place_order`**: Place a trading order.
    *   **Input**: `PlaceOrderParams` model (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `price`, etc.)
    *   **Output**: `OrderResponse` model (contains `order_id`) or an error dictionary.

2.  **`modify_order`**: Modify a pending order.
    *   **Input**: `ModifyOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, `trigger_price`, etc.)
    *   **Output**: `OrderResponse` model (contains `order_id`) or an error dictionary.

3.  **`cancel_order`**: Cancel a pending order.
    *   **Input**: `CancelOrderParams` model (see `models.py` for fields like `variety`, `order_id`)
    *   **Output**: `OrderResponse` model (contains `order_id`) or an error dictionary.

4.  **`get_orders`**: Retrieve all orders for the day.
    *   **Input**: `GetOrdersParams` model (currently empty).
    *   **Output**: `OrderHistoryResponse` model (contains a list of `orders`) or an error dictionary.

## Error Handling

The server catches common exceptions from the `pykiteconnect` library (e.g., `TokenException`, `InputException`, `OrderException`, `NetworkException`) and returns a JSON object with an `error` message and `details` about the specific Kite API error.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Use it at your own risk. Ensure you understand the Kite Connect API's rate limits and terms of service.
