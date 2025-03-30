# Zerodha Kite Connect MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect API (v3). It allows language models or other applications to manage trading orders through a standardized interface.

## Features

*   **Place Orders:** Place various types of orders (regular, AMO, CO, Iceberg, Auction).
*   **Modify Orders:** Modify attributes of pending regular or cover orders.
*   **Asynchronous:** Built with `httpx` for non-blocking API calls.
*   **Typed:** Uses Pydantic models for clear request/response structures and validation.
*   **Error Handling:** Maps Kite Connect API errors to specific Python exceptions.
*   **Configurable:** Uses environment variables for API credentials.

## Implemented Tools

*   `place_order(params: PlaceOrderParams) -> OrderIdResponse`
    *   Places a new trading order.
    *   Input: `PlaceOrderParams` model (includes variety, tradingsymbol, exchange, transaction\_type, order\_type, quantity, product, etc.)
    *   Output: `OrderIdResponse` model (contains the `order_id`).
*   `modify_order(params: ModifyOrderParams) -> OrderIdResponse`
    *   Modifies an existing pending order.
    *   Input: `ModifyOrderParams` model (includes variety, order\_id, and fields to modify like quantity, price, trigger\_price).
    *   Output: `OrderIdResponse` model (contains the `order_id`).

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
    *   Edit the `.env` file and add your Zerodha Kite Connect API credentials:
        *   `KITE_API_KEY`: Your application's API key.
        *   `KITE_ACCESS_TOKEN`: A valid access token. **Note:** Access tokens are short-lived and need to be generated periodically through the Kite Connect login flow (see [Kite Connect User API Docs](https://kite.trade/docs/connect/v3/user/)). This server assumes a valid token is provided via the environment variable.
        *   `KITE_API_BASE_URL` (Optional): Defaults to `https://api.kite.trade`.

## Running the Server

Use the `mcp` command-line tool (installed with `fastmcp`) to run the server:

```bash
mcp run main:mcp --port 8000
```

Replace `8000` with your desired port number.
The server will start, and the MCP tools (`place_order`, `modify_order`) will be available for interaction.

## Authentication

Authentication with the Kite Connect API is handled via the `KITE_API_KEY` and `KITE_ACCESS_TOKEN` provided in the `.env` file. Ensure the `KITE_ACCESS_TOKEN` is valid and refreshed as needed.

## Error Handling

The client (`client.py`) attempts to map common HTTP status codes and Kite API error responses (`error_type` field in JSON response) to specific Python exceptions (e.g., `AuthenticationError`, `ValidationError`, `InsufficientFundsError`, `RateLimitError`). Tools in `main.py` catch these exceptions and return a JSON object with an `"error"` key and often an `"error_type"` key.

## Rate Limits

The Kite Connect API has rate limits (e.g., 10 requests per second for order placement/modification). The client includes basic retry logic for rate limit errors (`RateLimitError`) and network issues (`NetworkError`) using the `tenacity` library. However, sustained high traffic might still hit limits. Implement more sophisticated rate limiting strategies if required.

## Environment Variables

*   `KITE_API_KEY` (Required): Your Kite Connect API key.
*   `KITE_ACCESS_TOKEN` (Required): Your Kite Connect access token.
*   `KITE_API_BASE_URL` (Optional): The base URL for the Kite API. Defaults to `https://api.kite.trade`.
