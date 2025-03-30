# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server built with FastMCP to interact with the Kite Connect Orders API (v3). It allows language models or other agents to place, modify, and cancel stock market orders using the `pykiteconnect` library.

## Features

*   **Place Orders:** Place regular, AMO, CO, Iceberg, and Auction orders.
*   **Modify Orders:** Modify pending regular or CO orders.
*   **Cancel Orders:** Cancel pending orders.
*   **Typed Inputs:** Uses Pydantic models for clear and validated input parameters.
*   **Error Handling:** Captures and reports specific exceptions from the `pykiteconnect` library.
*   **Asynchronous:** Leverages `asyncio` for non-blocking operations suitable for MCP environments.

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

4.  **Configure environment variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Kite Connect API Key and a valid Access Token:
        ```dotenv
        KITE_API_KEY="YOUR_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_ACCESS_TOKEN"
        ```
    *   **Important:** The `KITE_ACCESS_TOKEN` is short-lived (typically valid for one day). You need a separate process or mechanism to obtain a new access token daily using the Kite Connect login flow and update the `.env` file or environment variable accordingly before starting the server.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes are detected (useful for development).

The MCP server will be available at `http://localhost:8000` (or your machine's IP address).

## API Tools

The server exposes the following tools:

1.  **`place_order(params: PlaceOrderParams) -> Dict[str, Any]`**
    *   Description: Places a new order.
    *   Input: `PlaceOrderParams` model (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, etc.).
    *   Output: A dictionary containing `status: 'success'` and `data: {'order_id': '...'}` on success, or `status: 'error'` with details on failure.

2.  **`modify_order(params: ModifyOrderParams) -> Dict[str, Any]`**
    *   Description: Modifies an existing pending order.
    *   Input: `ModifyOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, etc.).
    *   Output: A dictionary containing `status: 'success'` and `data: {'order_id': '...'}` on success, or `status: 'error'` with details on failure.

3.  **`cancel_order(params: CancelOrderParams) -> Dict[str, Any]`**
    *   Description: Cancels an existing pending order.
    *   Input: `CancelOrderParams` model (see `models.py` for fields like `variety`, `order_id`).
    *   Output: A dictionary containing `status: 'success'` and `data: {'order_id': '...'}` on success, or `status: 'error'` with details on failure.

## Error Handling

The server catches exceptions raised by the `pykiteconnect` library (e.g., `TokenException`, `OrderException`, `InputException`) and returns a structured error response:

```json
{
  "status": "error",
  "message": "Invalid login credentials.",
  "error_type": "TokenException"
}
```

## Rate Limits

The Kite Connect API has rate limits (e.g., 3 requests per second for order placement/modification/cancellation). This MCP server *does not* implement explicit rate limiting itself. Calls exceeding the Kite API limits will result in errors returned by the API (`NetworkException` or similar). Ensure any client using this MCP respects these limits.

## Disclaimer

Trading in financial markets involves risk. This software is provided "as is" without warranty of any kind. Use it at your own risk and ensure you understand the implications of automated trading.
