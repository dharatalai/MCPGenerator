# Zerodha Kite Connect Orders MCP Server

This project provides a Model Context Protocol (MCP) server built with FastMCP to interact with the Zerodha Kite Connect v3 API, specifically for managing trading orders.

It allows language models or other applications to place and modify orders through a standardized MCP interface.

## Features

*   Place various types of orders (regular, AMO, CO, Iceberg, Auction).
*   Modify pending orders.
*   Asynchronous API interaction using `httpx`.
*   Input validation using Pydantic models.
*   Environment variable-based configuration.
*   Structured logging.
*   Basic Kite API error handling.

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
        *   `KITE_API_KEY`: Your Kite application's API key.
        *   `KITE_ACCESS_TOKEN`: A valid access token obtained through the Kite Connect login flow. **Note:** Access tokens are short-lived and need to be regenerated periodically.
        *   `KITE_BASE_URL` (Optional): Defaults to `https://api.kite.trade`.

## Running the Server

Start the MCP server using Uvicorn (which is included via FastMCP's run command):

```bash
python main.py
```

By default, the server will run on `http://127.0.0.1:8000` (or the host/port specified by `MCP_HOST`/`MCP_PORT` environment variables if set).

You can access the auto-generated OpenAPI documentation at `http://127.0.0.1:8000/docs`.

## Available Tools

The MCP server exposes the following tools:

1.  **`place_order`**
    *   **Description:** Places an order of a specified variety.
    *   **Parameters:** See the `PlaceOrderParams` model in `models.py` for detailed arguments and descriptions (e.g., `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `validity`, `price`, `trigger_price`, etc.).
    *   **Returns:** `Dict[str, str]` containing the `order_id` on success.

2.  **`modify_order`**
    *   **Description:** Modifies attributes of a pending regular or cover order.
    *   **Parameters:** See the `ModifyOrderParams` model in `models.py` (e.g., `variety`, `order_id`, `parent_order_id`, `order_type`, `quantity`, `price`, `trigger_price`, `validity`, etc.).
    *   **Returns:** `Dict[str, str]` containing the `order_id` on success.

## Error Handling

*   The API client (`client.py`) attempts to parse errors returned by the Kite Connect API and raises a `KiteApiException` with details (status code, error type, message).
*   Network errors (timeouts, connection issues) during the API call also raise `KiteApiException`.
*   Input validation errors (e.g., missing required fields, invalid values) are handled by Pydantic within the models (`models.py`) and will result in errors before the API call is made.
*   Unexpected server-side errors will raise standard Python exceptions.
*   MCP tools propagate `KiteApiException` directly, allowing clients to potentially handle specific API errors. Other exceptions are caught and re-raised as generic `RuntimeError`.

## Rate Limits

The Zerodha Kite Connect API has rate limits (typically around 10 requests per second for order operations, but check the official documentation for current limits).

This implementation **does not** include built-in client-side rate limiting. If you anticipate high request volumes, you may need to add rate limiting logic (e.g., using libraries like `aiolimiter`) either within the MCP tools or in the application calling the MCP server.

## Authentication

Authentication is handled via the `KITE_API_KEY` and `KITE_ACCESS_TOKEN` provided in the environment variables. Ensure the access token is valid and refreshed as needed.

## Disclaimer

Trading involves substantial risk. This code is provided as-is, without warranty. Ensure thorough testing in a simulated environment before using with real funds. The authors are not responsible for any financial losses incurred.
