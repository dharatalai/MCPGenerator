# KiteConnect Orders MCP Server

This project implements a Model Context Protocol (MCP) server for interacting with the order management endpoints of the Zerodha Kite Connect API v3. It allows language models or other applications to place, modify, and cancel trading orders programmatically via a standardized MCP interface.

This MCP focuses specifically on the order-related actions and does not cover other Kite Connect functionalities like fetching positions, holdings, market data, etc.

## Features

*   **Place Orders:** Place new orders of various types (regular, AMO, CO, Iceberg, Auction).
*   **Modify Orders:** Modify pending orders (quantity, price, trigger price, etc.).
*   **Cancel Orders:** Cancel pending orders.
*   **Typed Inputs:** Uses Pydantic models for clear and validated input parameters.
*   **Error Handling:** Maps Kite Connect API errors to specific exceptions and provides informative error messages.
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking I/O.

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
        *   `KITE_API_KEY`: Your application's API key.
        *   `KITE_ACCESS_TOKEN`: A valid access token obtained through the Kite Connect login flow. **Note:** Access tokens are typically valid for only one day. You need a mechanism to generate/refresh this token regularly.
        *   `KITE_BASE_URL`: (Optional) Defaults to `https://api.kite.trade`.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes are detected (useful for development).

The MCP server will be available at `http://localhost:8000` (or the specified host/port).

## Available Tools

The MCP server exposes the following tools:

1.  **`place_order`**
    *   **Description:** Places an order of a specified variety (regular, amo, co, iceberg, auction). Returns the `order_id` upon successful placement.
    *   **Input Model:** `PlaceOrderParams` (see `models.py` for fields: `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `price`, `trigger_price`, etc.)
    *   **Returns:** `OrderIdResponse` (`{"order_id": "string"}`) on success, or an error dictionary (`{"error": "ErrorType", "message": "..."}`).

2.  **`modify_order`**
    *   **Description:** Modifies attributes of an open or pending order. Applicable parameters depend on the order variety.
    *   **Input Model:** `ModifyOrderParams` (see `models.py` for fields: `variety`, `order_id`, `parent_order_id`, `order_type`, `quantity`, `price`, `trigger_price`, etc.)
    *   **Returns:** `OrderIdResponse` (`{"order_id": "string"}`) on success, or an error dictionary.

3.  **`cancel_order`**
    *   **Description:** Cancels an open or pending order.
    *   **Input Model:** `CancelOrderParams` (see `models.py` for fields: `variety`, `order_id`, `parent_order_id`)
    *   **Returns:** `OrderIdResponse` (`{"order_id": "string"}`) on success, or an error dictionary.

## Error Handling

The server attempts to catch errors from the Kite Connect API and return them in a structured format. Common error types include:

*   `InputException`: Invalid parameters provided in the request.
*   `TokenException`: Invalid or expired `api_key` or `access_token`.
*   `PermissionException`: The API key doesn't have permission for the requested action.
*   `NetworkException`: Could not connect to the Kite API servers or the request timed out.
*   `GeneralException`: Other API-level errors (e.g., insufficient funds, RMS rejections, order already executed/cancelled).
*   `RateLimitException`: Exceeded the allowed number of API requests per second.
*   `InternalServerError`: An unexpected error occurred within the MCP server itself.

The error response typically looks like:
`{"error": "ErrorTypeName", "message": "Detailed error message from API or server", "status_code": <HTTP_Status_Code>}`
