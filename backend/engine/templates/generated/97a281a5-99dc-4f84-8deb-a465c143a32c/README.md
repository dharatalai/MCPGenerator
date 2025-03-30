# Kite Connect Orders MCP Server

This project provides an MCP (Model Context Protocol) server for interacting with the Kite Connect Orders API. It allows language models or other applications to place, modify, and cancel stock market orders using natural language or structured requests via the MCP interface.

## Features

*   **Place Orders:** Supports various order types (regular, AMO, CO, Iceberg, Auction).
*   **Modify Orders:** Allows modification of pending regular and CO orders.
*   **Cancel Orders:** Enables cancellation of pending orders.
*   **Typed Inputs:** Uses Pydantic models for robust input validation.
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking I/O.
*   **Error Handling:** Provides informative error messages from the Kite API.

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
    *   Edit the `.env` file and add your Kite Connect `API KEY` and a valid `ACCESS TOKEN`.
        ```dotenv
        KITE_API_KEY=your_api_key
        KITE_ACCESS_TOKEN=your_access_token
        # KITE_API_BASE_URL=https://api.kite.trade # Optional override
        ```
    *   **Important:** The `ACCESS TOKEN` is obtained after a successful Kite Connect login flow (e.g., using the Python client library or manual login) and is typically short-lived.
You need a mechanism to refresh or provide a valid token.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp.app --reload --host 0.0.0.0 --port 8000
```

*   `--reload`: Enables auto-reloading for development.
*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.

The server will start, and the MCP tools will be available for interaction.

## Available Tools

The following tools are exposed by this MCP server:

1.  **`place_order(params: PlaceOrderParams)`**
    *   Description: Places an order of a specific variety.
    *   Input: `PlaceOrderParams` model (includes `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, and optional fields like `price`, `trigger_price`, etc.).
    *   Returns: `{"order_id": "<order_id>"}` on success, or an error dictionary.

2.  **`modify_order(params: ModifyOrderParams)`**
    *   Description: Modifies attributes of a pending regular or CO order.
    *   Input: `ModifyOrderParams` model (includes `variety`, `order_id`, and optional fields like `quantity`, `price`, `trigger_price`).
    *   Returns: `{"order_id": "<order_id>"}` on success, or an error dictionary.

3.  **`cancel_order(params: CancelOrderParams)`**
    *   Description: Cancels a pending order.
    *   Input: `CancelOrderParams` model (includes `variety`, `order_id`).
    *   Returns: `{"order_id": "<order_id>"}` on success, or an error dictionary.

Refer to `models.py` for the detailed structure of the input parameter models.

## Authentication

Authentication with the Kite Connect API is handled via the `KITE_API_KEY` and `KITE_ACCESS_TOKEN` provided in the `.env` file. Ensure the access token is valid and has the necessary permissions for order placement and modification.

## Error Handling

The server attempts to catch errors from the Kite Connect API (like insufficient funds, invalid parameters, network issues) and returns them in a structured JSON format:

```json
{
  "error": "Specific error message from Kite API or client.",
  "code": "KITE_ERROR_CODE", // Optional: Kite specific error type (e.g., InputException)
  "status": "error"
}
```

Check the server logs for more detailed error information and stack traces.

## Rate Limiting

The Kite Connect API has rate limits (e.g., 10 requests per second). The client includes a basic delay mechanism (`REQUEST_DELAY` in `client.py`) to mitigate hitting these limits. For high-throughput applications, a more sophisticated rate limiting strategy (e.g., token bucket) might be necessary.
