# Kite Connect MCP Server

This project implements a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect trading API (v3/v4) using the `pykiteconnect` library and `FastMCP`.

It provides tools for managing trading orders:
*   Placing new orders
*   Modifying existing pending orders
*   Cancelling existing pending orders

## Features

*   Exposes Kite Connect order management functions as MCP tools.
*   Uses Pydantic for robust data validation.
*   Handles Kite Connect API exceptions gracefully.
*   Loads API credentials securely from environment variables.
*   Asynchronous server implementation using FastMCP.

## Prerequisites

*   Python 3.8+
*   A Zerodha Kite Connect API key and secret.
*   A valid `access_token` obtained through the Kite Connect login flow.

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

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory by copying the example:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Kite Connect API key and a valid access token:
    ```env
    KITE_API_KEY="YOUR_API_KEY"
    KITE_ACCESS_TOKEN="YOUR_VALID_ACCESS_TOKEN"
    ```
    **Important:** The `KITE_ACCESS_TOKEN` is short-lived (typically valid for one day). You need a separate process or script to generate this token daily (using your API key and secret via the Kite Connect login flow) and update the `.env` file or environment variable before starting the MCP server.

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port number.
*   `--reload`: Automatically restarts the server when code changes (useful for development).

The server will start, and the MCP endpoint will be available at `http://localhost:8000/mcp`.

## Available Tools

The following tools are exposed via the MCP server:

### 1. `place_order`

*   **Description:** Places an order of a specified variety.
*   **Input Model:** `PlaceOrderParams`
    *   `variety`: `Variety` (Enum: regular, amo, co, iceberg, auction) - **Required**
    *   `tradingsymbol`: `str` - **Required**
    *   `exchange`: `Exchange` (Enum: NSE, BSE, NFO, CDS, MCX, BCD, BFO) - **Required**
    *   `transaction_type`: `TransactionType` (Enum: BUY, SELL) - **Required**
    *   `quantity`: `int` (> 0) - **Required**
    *   `product`: `Product` (Enum: CNC, NRML, MIS, MTF) - **Required**
    *   `order_type`: `OrderType` (Enum: MARKET, LIMIT, SL, SL-M) - **Required**
    *   `price`: `Optional[float]` (>= 0) - Required for LIMIT, SL orders.
    *   `trigger_price`: `Optional[float]` (>= 0) - Required for SL, SL-M orders.
    *   `disclosed_quantity`: `Optional[int]` (>= 0)
    *   `validity`: `Optional[Validity]` (Enum: DAY, IOC, TTL) - Default: DAY
    *   `validity_ttl`: `Optional[int]` (1-1440) - Required if validity is TTL.
    *   `iceberg_legs`: `Optional[int]` (2-10) - Required if variety is iceberg.
    *   `iceberg_quantity`: `Optional[int]` (>= 1) - Required if variety is iceberg.
    *   `auction_number`: `Optional[str]` - Required if variety is auction.
    *   `tag`: `Optional[str]` (max 20 chars)
*   **Returns:** `Dict[str, str]` - e.g., `{"order_id": "230720000000001"}` on success, or `{"error": "...", "details": {...}}` on failure.

### 2. `modify_order`

*   **Description:** Modifies attributes of a pending regular or cover order.
*   **Input Model:** `ModifyOrderParams`
    *   `variety`: `Variety` (Enum: regular, co, etc.) - **Required**
    *   `order_id`: `str` - **Required**
    *   `parent_order_id`: `Optional[str]`
    *   `quantity`: `Optional[int]` (> 0)
    *   `price`: `Optional[float]` (>= 0)
    *   `order_type`: `Optional[OrderType]` (Cannot change to/from MARKET)
    *   `trigger_price`: `Optional[float]` (>= 0)
    *   `validity`: `Optional[Validity]` (Enum: DAY, IOC - Cannot change to TTL)
    *   `disclosed_quantity`: `Optional[int]` (>= 0)
*   **Returns:** `Dict[str, str]` - e.g., `{"order_id": "230720000000001"}` on success, or `{"error": "...", "details": {...}}` on failure.

### 3. `cancel_order`

*   **Description:** Cancels a pending regular or cover order.
*   **Input Model:** `CancelOrderParams`
    *   `variety`: `Variety` (Enum: regular, co, amo, iceberg, auction) - **Required**
    *   `order_id`: `str` - **Required**
    *   `parent_order_id`: `Optional[str]`
*   **Returns:** `Dict[str, str]` - e.g., `{"order_id": "230720000000001"}` on success, or `{"error": "...", "details": {...}}` on failure.

## Error Handling

The server catches exceptions from the `pykiteconnect` library and returns a JSON response with an `error` key containing a descriptive message and optionally a `details` key with more specific information (like Kite API error codes).

Common errors include:
*   `InputException`: Invalid parameters provided.
*   `TokenException`: Invalid or expired `access_token`.
*   `PermissionException`: API key doesn't have permission for the action.
*   `OrderException`: Order placement/modification/cancellation failed (e.g., insufficient funds, validation errors).
*   `NetworkException`: Could not connect to the Kite API servers.
*   `GeneralException`: Other API-level errors.

## Rate Limiting

The Kite Connect API has rate limits (e.g., 3 requests per second for order operations). This MCP server currently relies on `pykiteconnect`'s internal handling or expects the user to manage call frequency. Exceeding limits will result in errors from the API.

## TODO / Potential Enhancements

*   Implement dynamic `access_token` refresh mechanism.
*   Add tools for other Kite Connect functionalities (fetching orders, trades, positions, holdings, instruments, historical data, MF orders, GTT orders).
*   Implement WebSocket connection for live market data streaming (would require significant changes).
*   Add explicit rate limiting within the MCP server.
*   More sophisticated configuration management.
*   Add unit and integration tests.
