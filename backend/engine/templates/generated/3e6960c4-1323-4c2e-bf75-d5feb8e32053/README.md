# Kite Connect Orders MCP Server

This project provides an MCP (Model Context Protocol) server for interacting with the Zerodha Kite Connect API v3, specifically focusing on order management functionalities.

It allows language models or other applications to place and modify trading orders through a standardized MCP interface.

## Features

*   **Place Orders:** Place various types of orders (Regular, AMO, CO, Iceberg, Auction).
*   **Modify Orders:** Modify attributes of pending orders.
*   **Typed Interface:** Uses Pydantic models for clear and validated inputs and outputs.
*   **Asynchronous:** Built with `asyncio` and `httpx` for non-blocking I/O.
*   **Error Handling:** Maps Kite Connect API errors to specific exceptions.
*   **Configurable:** Uses environment variables for API credentials and base URL.

## Prerequisites

*   Python 3.8+
*   A Zerodha Kite Connect API Key and Secret.
*   A valid `access_token` obtained through the Kite Connect login flow (this needs to be generated daily).

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
    *   Edit the `.env` file and add your Kite Connect `API_KEY` and a valid `ACCESS_TOKEN`:
        ```dotenv
        KITE_API_KEY="YOUR_ACTUAL_API_KEY"
        KITE_ACCESS_TOKEN="YOUR_VALID_ACCESS_TOKEN"
        KITE_API_BASE_URL="https://api.kite.trade"
        ```
    *   **Important:** The `ACCESS_TOKEN` is short-lived and needs to be updated regularly (typically daily) after completing the Kite Connect login flow.

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will start, usually on `http://127.0.0.1:8000` (unless configured otherwise).

## Available Tools

The MCP server exposes the following tools:

1.  **`place_order`**
    *   **Description:** Places an order of a specified variety.
    *   **Input:** `PlaceOrderParams` model (see `models.py` for details).
        *   Requires fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `order_type`, `quantity`, `product`, `validity`, and conditionally required fields like `price`, `trigger_price`, etc., based on order type and variety.
    *   **Output:** `OrderResponse` model containing the `order_id` on success, or an error dictionary.

2.  **`modify_order`**
    *   **Description:** Modifies attributes of a pending order.
    *   **Input:** `ModifyOrderParams` model (see `models.py` for details).
        *   Requires `variety` and `order_id`.
        *   Optional fields for modification include `order_type`, `quantity`, `price`, `trigger_price`, `disclosed_quantity`, `validity` (restrictions apply based on order variety).
    *   **Output:** `OrderResponse` model containing the `order_id` on success, or an error dictionary.

## Error Handling

The client attempts to map common Kite Connect API errors and HTTP status codes to specific Python exceptions (defined in `client.py`). These errors are caught by the tool functions in `main.py` and returned as a JSON dictionary with `error` and `error_type` keys.

Example error response:
```json
{
  "error": "InputException (HTTP 400): Invalid `trigger_price`.",
  "error_type": "InvalidInputError"
}
```

## Rate Limiting

The Kite Connect API has rate limits (e.g., 10 requests per second for order placement/modification). This client includes basic retry logic for potential network issues and rate limit errors (HTTP 429), but robust handling might require more sophisticated client-side throttling if you expect high request volumes.

## Disclaimer

Trading involves substantial risk. This software is provided "as is" without warranty of any kind. Ensure you understand the risks and the behavior of the Kite Connect API before using this tool for live trading. Test thoroughly in a simulated environment if possible.
