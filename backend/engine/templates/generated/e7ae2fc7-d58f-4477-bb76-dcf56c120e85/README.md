# Zerodha Kite Connect Orders MCP Server

This MCP (Model Context Protocol) server provides tools for managing orders (placing, modifying, cancelling, retrieving) using the Zerodha Kite Connect API v3.

It exposes Kite Connect order functionalities as callable tools for language models or other applications via the MCP standard.

## Features

*   Place various types of orders (regular, AMO, CO, Iceberg).
*   Built using `FastMCP`.
*   Asynchronous API client (`httpx`).
*   Typed requests and responses using `Pydantic`.
*   Handles API authentication, errors, timeouts, and basic retries.
*   Configurable via environment variables.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
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

## Configuration

Configuration is managed through environment variables. Create a `.env` file in the project root directory by copying the example file:

```bash
cp .env.example .env
```

Now, edit the `.env` file and add your Zerodha Kite Connect API credentials:

*   `KITE_API_KEY`: Your application's API key obtained from the [Kite Developer Console](https://developers.kite.trade/).
*   `KITE_ACCESS_TOKEN`: The access token generated after a successful Kite Connect login flow. **Note:** Access tokens are typically short-lived and need to be regenerated periodically. This server implementation assumes a valid access token is provided via the environment variable. You will need a separate process or mechanism to handle the Kite Connect login flow and update the `KITE_ACCESS_TOKEN`.
*   `KITE_ROOT_URL`: The base URL for the Kite Connect API. Defaults to `https://api.kite.trade` (live environment).

## Running the Server

Use `uvicorn` to run the FastMCP application:

```bash
# For development with auto-reload
uvicorn main:mcp.app --reload

# For production
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 
```

The server will start, and you can interact with it using an MCP client at `http://127.0.0.1:8000` (or the host/port you specified).

## Available Tools

The following tools are exposed by this MCP server:

### `place_order`

*   **Description:** Place an order of a specific variety (regular, amo, co, iceberg, auction).
*   **Parameters:**
    *   `variety` (string, required): Order variety (`regular`, `amo`, `co`, `iceberg`, `auction`).
    *   `tradingsymbol` (string, required): Tradingsymbol of the instrument (e.g., `INFY`, `NIFTY21JUNFUT`).
    *   `exchange` (string, required): Name of the exchange (`NSE`, `BSE`, `NFO`, `CDS`, `BCD`, `MCX`).
    *   `transaction_type` (string, required): Transaction type (`BUY` or `SELL`).
    *   `order_type` (string, required): Order type (`MARKET`, `LIMIT`, `SL`, `SL-M`).
    *   `quantity` (integer, required): Quantity to transact (must be positive).
    *   `product` (string, required): Product type (`CNC`, `NRML`, `MIS`, `MTF`).
    *   `price` (float, optional): The price for `LIMIT` or `SL` orders. Required for `LIMIT`/`SL`.
    *   `trigger_price` (float, optional): The trigger price for `SL`, `SL-M`, or `CO` orders. Required for `SL`/`SL-M`.
    *   `disclosed_quantity` (integer, optional): Quantity to disclose publicly (equity only, non-negative).
    *   `validity` (string, optional): Order validity (`DAY`, `IOC`, `TTL`). Defaults to `DAY`.
    *   `validity_ttl` (integer, optional): Order life span in minutes. Required if `validity` is `TTL`.
    *   `iceberg_legs` (integer, optional): Total number of legs for iceberg order (2-10). Required if `variety` is `iceberg`.
    *   `tag` (string, optional): An optional tag for the order (Max 20 chars).
*   **Returns:** A dictionary containing `{"order_id": "..."}` on success, or an error dictionary (e.g., `{"status": "error", "message": "...", "error_type": "..."}`) on failure.

## Error Handling

The server catches common errors:
*   **Validation Errors:** If input parameters don't match the required format or constraints.
*   **Authentication Errors:** If the `KITE_API_KEY` or `KITE_ACCESS_TOKEN` is invalid or expired (HTTP 403).
*   **Bad Request Errors:** If the Kite API rejects the request due to invalid parameters (HTTP 400).
*   **Rate Limit Errors:** If the application exceeds Kite API rate limits (HTTP 429). Basic retry logic is implemented.
*   **Network Errors:** Timeouts or connection issues when communicating with the Kite API.
*   **Server Errors:** If the Kite API experiences internal issues (HTTP 5xx). Basic retry logic is implemented.
*   **Internal Server Errors:** Unexpected errors within the MCP server itself.

Error responses are returned as JSON objects with `status`, `message`, and `error_type` fields.
