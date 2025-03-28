# Zerodha Kite Connect MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect API (v3). It allows language models or other applications to manage trading orders (place, modify, cancel) and retrieve order information through a standardized MCP interface.

## Features

*   **Place Orders:** Supports various order types (regular, amo, co, iceberg, auction).
*   **Modify Orders:** Allows modification of pending regular and CO orders.
*   **Cancel Orders:** Cancel pending orders.
*   **Get Orders:** Retrieve the list of all orders for the current trading day.
*   **Get Order History:** Fetch the status change history for a specific order.
*   Built with **FastMCP** for easy integration.
*   Asynchronous API client using **httpx**.
*   Input validation using **Pydantic**.
*   Basic error handling and logging.

## Prerequisites

*   Python 3.8+
*   Zerodha Kite Connect API Key and Secret.
*   A valid Zerodha Kite Connect Access Token (obtained via the Kite Connect login flow - see [Kite Connect Documentation](https://kite.trade/docs/connect/v3/user/)). **Note:** Access tokens are short-lived and need to be refreshed periodically. This server assumes a valid token is provided via environment variables.

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
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Kite Connect API Key and a valid Access Token:
    ```dotenv
    # Zerodha Kite Connect API Credentials and Configuration
    KITE_API_KEY="YOUR_ACTUAL_API_KEY"
    KITE_ACCESS_TOKEN="YOUR_VALID_ACCESS_TOKEN"
    KITE_BASE_URL="https://api.kite.trade"
    ```

## Running the Server

Use `uvicorn` to run the MCP server:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes (useful for development).

The MCP server will be available at `http://localhost:8000` (or the specified host/port).

## Available Tools

The following tools are exposed via the MCP server:

*   `place_order(params: PlaceOrderParams)`: Place an order.
*   `modify_order(params: ModifyOrderParams)`: Modify a pending order.
*   `cancel_order(params: CancelOrderParams)`: Cancel a pending order.
*   `get_orders()`: Retrieve all orders for the day.
*   `get_order_history(params: GetOrderHistoryParams)`: Retrieve the history for a specific order.

Refer to `models.py` for the detailed structure of the input parameter models (`PlaceOrderParams`, `ModifyOrderParams`, etc.).

## Error Handling

The server attempts to catch errors from the Kite Connect API (like invalid parameters, authentication issues, insufficient funds, exchange rejections) and network issues. Errors are generally returned as a JSON dictionary with an `"error"` key, often including details like `"status_code"` and `"error_type"` from the API.

```json
{
  "error": "Invalid order parameters.",
  "status_code": 400,
  "error_type": "InputException"
}
```

## Rate Limiting

The Kite Connect API has rate limits (e.g., 3 requests per second for order-related endpoints). The client includes basic retry logic with backoff for `429 Too Many Requests` errors and transient network issues. However, sustained high request rates will still result in errors after retries are exhausted.

## Important Notes

*   **Access Token Management:** This server requires a *pre-generated* access token. In a production environment, you would need a robust mechanism to handle the Kite Connect login flow and periodically refresh the access token.
*   **Security:** Ensure your API Key and Access Token are kept secure and are not exposed publicly.
*   **Disclaimer:** Trading involves risks. Use this software responsibly and test thoroughly in a simulated environment if possible before using with real funds.
