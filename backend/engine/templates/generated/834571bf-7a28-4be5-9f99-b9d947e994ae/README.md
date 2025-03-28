# Zerodha Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect v3 API, specifically focusing on order management functionalities.

It allows language models or other applications to place, modify, cancel, and retrieve orders through a standardized MCP interface, powered by FastMCP.

## Features

This MCP server exposes the following tools:

*   **`place_order`**: Place an order of a particular variety (regular, amo, co, iceberg, auction).
*   **`modify_order`**: Modify an open or pending order.
*   **`cancel_order`**: Cancel an open or pending order.
*   **`get_orders`**: Retrieve the list of all orders (open, pending, executed) for the day.

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
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Zerodha Kite Connect API credentials:
        *   `KITE_API_KEY`: Your application's API key.
        *   `KITE_ACCESS_TOKEN`: The access token generated after a user logs in via Kite Connect. **Note:** This token is typically valid only for the day it's generated. You will need a separate process (e.g., a manual login flow or an automated mechanism if feasible) to obtain a valid `access_token` each day before running the server.
        *   `KITE_BASE_URL`: The base URL for the API (default is usually correct).

## Running the Server

Once the setup is complete, you can run the MCP server using Uvicorn:

```bash
python main.py
# Or directly with uvicorn for more control:
# uvicorn main:mcp.app --reload --host 0.0.0.0 --port 8000
```

The server will start, typically on `http://127.0.0.1:8000` (unless configured otherwise).

## API Client (`client.py`)

The `client.py` file contains the `ZerodhaKiteClient` class responsible for:

*   Making asynchronous requests to the Kite Connect API.
*   Handling authentication headers (`Authorization`, `X-Kite-Version`).
*   Parsing responses and checking for API-specific errors.
*   Mapping HTTP status codes and API errors to a custom `KiteApiException`.
*   Basic request/response logging.

## Models (`models.py`)

The `models.py` file defines Pydantic models for:

*   **Enums:** Representing fixed sets of values used by the API (e.g., `OrderVariety`, `TransactionType`, `ExchangeType`).
*   **Input Parameters:** Defining the expected structure and validation rules for data passed to each MCP tool (e.g., `PlaceOrderParams`, `ModifyOrderParams`).
*   **Return Types:** Defining the structure of successful responses (e.g., `OrderIDResponse`, `Order`).
*   **Error Response:** A standard structure (`KiteErrorResponse`) for returning errors from the MCP tools.

## Error Handling

The server attempts to catch errors at different levels:

1.  **HTTP Errors:** The `ZerodhaKiteClient` catches `httpx.HTTPStatusError` and maps common status codes (4xx, 5xx) to `KiteApiException` with appropriate error types (e.g., `AuthenticationError`, `InputException`, `GeneralException`, `RateLimitError`).
2.  **Kite API Errors:** If the API returns a `200 OK` status but includes an error message in the response body (`{"status": "error", ...}`), the client parses this and raises a `KiteApiException`.
3.  **Network/Request Errors:** `httpx.RequestError` is caught for issues like timeouts or connection problems, resulting in a `NetworkException`.
4.  **Validation Errors:** Pydantic models in `models.py` perform initial validation on input parameters.
5.  **Unexpected Errors:** Generic exceptions are caught in the MCP tool implementations and returned as a `InternalServerError` or similar.

Failed tool executions return a JSON dictionary conforming to the `KiteErrorResponse` model.

## Important Considerations

*   **Access Token Management:** The biggest challenge with Kite Connect is managing the daily `access_token`. This MCP server *assumes* a valid token is provided via the environment variable. You need a separate process to handle the Kite Connect login flow and update the `KITE_ACCESS_TOKEN` daily.
*   **Rate Limiting:** The Kite API enforces rate limits (e.g., 10 requests/second for orders). The client currently handles `429 Too Many Requests` errors by raising a `RateLimitError`. Implement retry logic or client-side delays if needed, although relying on the API's 429 response is often sufficient.
*   **Security:** Never commit your `.env` file with real credentials to version control. Ensure the server running this MCP is secured appropriately.
