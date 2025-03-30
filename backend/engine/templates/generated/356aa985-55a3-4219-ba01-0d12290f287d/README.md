# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server built with FastMCP to interact with the Zerodha Kite Connect Orders API. It allows language models or other applications to place, modify, and cancel stock market orders through a standardized interface.

## Features

*   **Place Orders:** Place various types of orders (regular, AMO, CO, Iceberg, Auction).
*   **Modify Orders:** Modify pending regular or CO orders.
*   **Cancel Orders:** Cancel pending orders.
*   **Typed Interface:** Uses Pydantic models for clear and validated input/output.
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking I/O.
*   **Error Handling:** Maps Kite API errors to specific Python exceptions.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Kite Connect API credentials:
        *   `KITE_API_KEY`: Your application's API key from Kite Developer.
        *   `KITE_ACCESS_TOKEN`: A valid access token obtained through the Kite Connect login flow. **Note:** Access tokens are typically short-lived and need to be refreshed or regenerated.
        *   `KITE_API_BASE_URL`: (Optional) Defaults to `https://api.kite.trade`.

## Running the Server

Use an ASGI server like Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes (for development).

The MCP server will be available at `http://localhost:8000` (or the specified host/port).

## Available Tools

The server exposes the following tools compatible with the MCP specification:

1.  **`place_order`**
    *   **Description:** Place an order of a particular variety.
    *   **Input:** `PlaceOrderParams` model (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, etc.).
    *   **Output:** Dictionary containing the `order_id` on success, or an `ErrorResponse` dictionary on failure.

2.  **`modify_order`**
    *   **Description:** Modify attributes of a pending regular or CO order.
    *   **Input:** `ModifyOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, `trigger_price`, etc.).
    *   **Output:** Dictionary containing the `order_id` on success, or an `ErrorResponse` dictionary on failure.

3.  **`cancel_order`**
    *   **Description:** Cancel a pending order.
    *   **Input:** `CancelOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `parent_order_id`).
    *   **Output:** Dictionary containing the `order_id` on success, or an `ErrorResponse` dictionary on failure.

## Authentication

Authentication is handled via the `KITE_API_KEY` and `KITE_ACCESS_TOKEN` environment variables, which are passed in the `Authorization` header of requests to the Kite Connect API.

**Important:** Managing the lifecycle of the `KITE_ACCESS_TOKEN` (obtaining and refreshing it) is outside the scope of this basic MCP server implementation and needs to be handled by your application's authentication flow.

## Error Handling

The `KiteConnectClient` attempts to map HTTP status codes and error messages from the Kite API to specific exceptions (e.g., `KiteInputException`, `KiteTokenException`, `KiteOrderException`). These are caught in `main.py` and returned as structured `ErrorResponse` dictionaries.
