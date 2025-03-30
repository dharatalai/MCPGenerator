# KiteConnect Orders MCP Server

This project provides a Model Context Protocol (MCP) server that acts as a wrapper around the Zerodha Kite Connect v3 API, specifically focusing on order management functionalities.

It allows language models or other MCP clients to interact with Kite Connect to place and modify trading orders programmatically.

## Features

*   **Place Orders:** Place various types of orders (regular, AMO, CO, Iceberg, Auction) across different exchanges.
*   **Modify Orders:** Modify attributes of existing pending orders (e.g., price, quantity, trigger price).
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking I/O.
*   **Typed:** Uses Pydantic for request and response validation.
*   **Error Handling:** Provides structured error responses for API and validation issues.
*   **Configurable:** API keys and tokens are managed via environment variables.
*   **Rate Limiting:** Includes a basic rate limiter to comply with Kite API limits (10 requests/second).

## Implemented Tools

1.  **`place_order`**: 
    *   Description: Place an order of a specific variety (regular, amo, co, iceberg, auction).
    *   Input: `PlaceOrderParams` model (see `models.py` for details).
    *   Output: `OrderResponse` containing the `order_id` or `ErrorResponse`.

2.  **`modify_order`**: 
    *   Description: Modify an open or pending order of a given variety.
    *   Input: `ModifyOrderParams` model (see `models.py` for details).
    *   Output: `OrderResponse` containing the `order_id` or `ErrorResponse`.

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
        *   `KITE_API_KEY`: Your application's API key from the Kite Developer console.
        *   `KITE_ACCESS_TOKEN`: A valid access token. **Important:** Access tokens are typically valid for only one trading day. You need a separate process or script to generate a new access token daily using the Kite Connect login flow and update the `.env` file or environment variable accordingly before running the server.
        *   `KITE_API_BASE_URL`: Defaults to `https://api.kite.trade`. Usually does not need to be changed.

## Running the Server

You can run the MCP server using an ASGI server like Uvicorn:

```bash
uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Enables auto-reloading when code changes (useful for development).

The server will start, and MCP clients can connect to it at `http://<your-server-ip>:8000`.

## Usage

Once the server is running, MCP clients can discover and call the available tools (`place_order`, `modify_order`) by sending requests according to the Model Context Protocol specification.
The input parameters for each tool must conform to the Pydantic models defined in `models.py`.

## Error Handling

The server returns structured `ErrorResponse` objects in case of failures:
*   **Validation Errors:** If the input parameters provided by the client do not match the required schema.
*   **Kite API Errors:** If the Kite Connect API returns an error (e.g., insufficient funds, invalid order parameters, invalid session).
The error message and status code from the API are included.
*   **Network/Timeout Errors:** If the server cannot reach the Kite Connect API.
*   **Initialization Errors:** If the server failed to start correctly (e.g., missing API keys).
*   **Unexpected Errors:** For any other server-side issues.

## Rate Limiting

The Kite Connect API has rate limits (typically 10 requests per second per user+API key). The client includes a simple asynchronous rate limiter to help prevent exceeding these limits. If the limit is hit, requests will be delayed automatically.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Ensure you understand the risks and the behavior of the Kite Connect API before using this tool for live trading. The authors are not responsible for any financial losses incurred.
