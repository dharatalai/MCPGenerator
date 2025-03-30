# KiteConnectTrading MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the Zerodha Kite Connect V3 trading API. It provides tools focused on order management: placing, modifying, and cancelling orders.

This server is built using [FastMCP](https://github.com/cognosis-ai/fastmcp).

## Features

*   **Place Orders:** Submit new orders of various types (regular, AMO, CO, iceberg, auction).
*   **Modify Orders:** Change parameters of existing pending orders (regular, CO).
*   **Cancel Orders:** Cancel existing pending orders.
*   **Typed Inputs:** Uses Pydantic models for robust input validation.
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking API calls.
*   **Error Handling:** Captures and reports common Kite API errors.

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
        *   `KITE_API_KEY`: Your Kite application's API key.
        *   `KITE_ACCESS_TOKEN`: A valid access token. 
            *   **Important:** You need to obtain this token separately using the Kite Connect login flow (e.g., using the official `kiteconnect-python` library or your own implementation). Access tokens are typically short-lived (valid for a day).
        *   `KITE_BASE_URL` (Optional): Defaults to `https://api.kite.trade`.

## Running the Server

Use an ASGI server like Uvicorn to run the application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes (for development).

The MCP server will be available at `http://localhost:8000`.

## Environment Variables

*   `KITE_API_KEY` (Required): Your Kite Connect API Key.
*   `KITE_ACCESS_TOKEN` (Required): The access token obtained via the Kite Connect login flow.
*   `KITE_BASE_URL` (Optional): The base URL for the Kite API. Defaults to `https://api.kite.trade`.

## API Tools

The following tools are exposed by this MCP server:

1.  **`place_order`**
    *   **Description:** Places an order of a specified variety (regular, amo, co, iceberg, auction) with the given parameters.
    *   **Input Model:** `PlaceOrderParams` (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `validity`, `price`, `trigger_price`, etc.)
    *   **Returns:** `OrderIDResponse` (e.g., `{"order_id": "230725000000001"}`) or `KiteApiError` on failure.

2.  **`modify_order`**
    *   **Description:** Modifies specific attributes of an open or pending order (only 'regular' and 'co' varieties supported by Kite API for modification).
    *   **Input Model:** `ModifyOrderParams` (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, `trigger_price`, etc.)
    *   **Returns:** `OrderIDResponse` (e.g., `{"order_id": "230725000000001"}`) or `KiteApiError` on failure.

3.  **`cancel_order`**
    *   **Description:** Cancels an open or pending order.
    *   **Input Model:** `CancelOrderParams` (see `models.py` for fields like `variety`, `order_id`, `parent_order_id`)
    *   **Returns:** `OrderIDResponse` (e.g., `{"order_id": "230725000000001"}`) or `KiteApiError` on failure.

## Error Handling

The tools will return a `KiteApiError` dictionary if the Kite API client encounters an error (e.g., invalid input, authentication failure, network issues, insufficient funds, rate limits). The error dictionary includes an `error_type` (like `InputException`, `TokenException`, `NetworkException`, `OrderException`) and a descriptive `message`.
