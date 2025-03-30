# Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect Orders API (v3). It allows language models or other agents to place and modify stock market orders through a standardized interface.

## Features

*   **Place Orders:** Supports placing various order types (regular, AMO, CO, Iceberg, Auction) via the `place_order` tool.
*   **Modify Orders:** Supports modifying pending orders (quantity, price, trigger price, etc.) via the `modify_order` tool.
*   **Typed Interface:** Uses Pydantic models for clear and validated input parameters.
*   **Asynchronous:** Built with `asyncio` and `httpx` for efficient I/O operations.
*   **Error Handling:** Captures and reports common API errors (authentication, rate limits, input errors, server errors).
*   **Configuration:** Uses environment variables for API credentials.

## Prerequisites

*   Python 3.8+
*   A Zerodha Kite Connect API key and a valid access token. You can get these from the [Kite Developer Console](https://developers.kite.trade/).
*   Understanding of the Kite Connect API v3, especially order parameters and potential error conditions.

## Setup

1.  **Clone the repository (or create the files):**
    ```bash
    # If cloned
    git clone <repository_url>
    cd kite_connect_mcp
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

4.  **Configure environment variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Kite Connect `API_KEY` and `ACCESS_TOKEN`:
        ```dotenv
        KITE_API_KEY="YOUR_ACTUAL_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_GENERATED_ACCESS_TOKEN"
        # KITE_BASE_URL="https://api.kite.trade" # Optional
        ```
    *   **Important:** The `ACCESS_TOKEN` is short-lived and needs to be generated regularly using the Kite Connect login flow. This MCP server assumes a valid token is provided via the environment variable.

## Running the Server

Start the MCP server using:

```bash
pip install uvicorn # If not already installed via requirements
python main.py
```

By default, the server will run on `http://127.0.0.1:8080` (FastMCP's default). You can check the server logs for the exact address.

The server exposes the following endpoints for MCP interaction:

*   `GET /` : Returns the MCP manifest describing the service and tools.
*   `POST /invoke/{tool_name}`: Executes the specified tool.

## Available Tools

### 1. `place_order`

Places a new order.

*   **Description:** Places an order of a specified variety (regular, amo, co, iceberg, auction). Does not guarantee execution.
*   **Input Model:** `PlaceOrderParams` (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `validity`, etc.)
*   **Returns:** A dictionary containing `{"order_id": "<order_id>"}` on success, or an error dictionary (`{"status": "error", "message": "...", "error_type": "..."}`) on failure.

### 2. `modify_order`

Modifies an existing pending order.

*   **Description:** Modifies attributes of a pending regular order (e.g., quantity, price). For Cover Orders (CO), only trigger_price can be modified.
*   **Input Model:** `ModifyOrderParams` (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, `trigger_price`, etc.)
*   **Returns:** A dictionary containing `{"order_id": "<order_id>"}` on successful modification, or an error dictionary on failure.

## Error Handling

The client (`client.py`) attempts to catch various errors:

*   **Authentication Errors:** Invalid `api_key` or `access_token` (HTTP 403).
*   **Bad Request Errors:** Invalid input parameters (HTTP 400, Kite `InputException`).
*   **Rate Limit Errors:** Exceeding API request limits (HTTP 429).
*   **Server Errors:** Issues on the Kite Connect server side (HTTP 5xx).
*   **Network Errors:** Timeouts or connection problems.
*   **API-Specific Errors:** Errors returned in the JSON response body by Kite (e.g., `OrderException`, `TokenException`).

Errors are returned to the MCP caller in a structured format:

```json
{
  "status": "error",
  "message": "Descriptive error message",
  "error_type": "ErrorCategory" // e.g., AuthenticationError, BadRequestError, RateLimitError, APIError
}
```

## Important Considerations

*   **Access Token Management:** This server requires a *pre-generated*, valid `access_token`. Implementing the full OAuth2 login flow to generate this token is outside the scope of this basic MCP server.
*   **Rate Limits:** The Kite Connect API has rate limits (e.g., 10 requests/second for order placement/modification). While the server handles 429 errors, it doesn't implement client-side rate limiting. High-frequency usage might require additional logic.
*   **Security:** Ensure your API key and access token are kept secure. Do not commit them directly into your code.
*   **Disclaimer:** Trading involves risks. Use this tool responsibly and ensure you understand the behavior of the Kite Connect API and the orders you are placing/modifying.
