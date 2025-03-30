# KiteConnect MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the Zerodha Kite Connect API (v3). It allows agents or applications to perform trading-related actions like generating sessions, placing orders, and modifying orders through a standardized MCP interface.

## Features

*   **Session Management**: Generate user sessions using a `request_token`.
*   **Order Placement**: Place various types of orders (regular, AMO, CO, Iceberg, Auction).
*   **Order Modification**: Modify pending regular and cover orders.
*   **Typed Interface**: Uses Pydantic models for clear and validated inputs.
*   **Error Handling**: Provides informative error messages from the Kite Connect API.

## Setup

1.  **Clone the repository (or create the files):**
    ```bash
    # If cloned
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

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Kite Connect API Key and API Secret:
        ```dotenv
        KITE_API_KEY="YOUR_API_KEY"
        KITE_API_SECRET="YOUR_API_SECRET"
        ```
        *(You get these credentials after creating an app on the [Kite Developer Console](https://developers.kite.trade/)).*

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes (useful for development).

The MCP server will be available at `http://localhost:8000`.

## Authentication Flow

1.  **Obtain `request_token`**: The user must first log in via the Kite Connect API login flow provided by Zerodha. After successful login and consent, Kite Connect redirects the user back to your registered redirect URL with a `request_token` appended as a query parameter.
2.  **Generate Session**: Use the `generate_session` tool provided by this MCP server, passing the obtained `request_token`.
    ```json
    {
      "tool_name": "generate_session",
      "arguments": {
        "params": {
          "request_token": "THE_OBTAINED_REQUEST_TOKEN"
        }
      }
    }
    ```
3.  **Receive `access_token`**: The tool will return a JSON response containing session details, including the crucial `access_token`.
    ```json
    {
        "user_id": "AB1234",
        "user_name": "Example Name",
        // ... other fields
        "access_token": "THE_GENERATED_ACCESS_TOKEN",
        "public_token": "..."
        // ...
    }
    ```
4.  **Use `access_token`**: Store this `access_token` securely. Pass it as the first argument (`access_token`) to all subsequent authenticated tool calls (`place_order`, `modify_order`). The access token is typically valid for one day.

## Available Tools

### 1. `generate_session`

*   **Description**: Generate a user session and obtain an access token using a request token.
*   **Input**: `GenerateSessionParams` model (`request_token`: string)
*   **Returns**: Dictionary containing session details, including `access_token`.

### 2. `place_order`

*   **Description**: Place an order of a specific variety.
*   **Input**: `access_token`: string, `params`: `PlaceOrderParams` model (see `models.py` for fields like `variety`, `tradingsymbol`, `exchange`, `transaction_type`, `quantity`, `product`, `order_type`, etc.)
*   **Returns**: Dictionary containing the `order_id` or an `error` message.
*   **Example Argument Structure**:
    ```json
    {
        "access_token": "THE_STORED_ACCESS_TOKEN",
        "params": {
            "variety": "regular",
            "exchange": "NSE",
            "tradingsymbol": "INFY",
            "transaction_type": "BUY",
            "quantity": 1,
            "product": "CNC",
            "order_type": "LIMIT",
            "price": 1500.00
        }
    }
    ```

### 3. `modify_order`

*   **Description**: Modify a pending regular or cover order.
*   **Input**: `access_token`: string, `params`: `ModifyOrderParams` model (see `models.py` for fields like `variety`, `order_id`, `quantity`, `price`, etc.)
*   **Returns**: Dictionary containing the `order_id` of the modified order or an `error` message.
*   **Example Argument Structure**:
    ```json
    {
        "access_token": "THE_STORED_ACCESS_TOKEN",
        "params": {
            "variety": "regular",
            "order_id": "230101000000001",
            "quantity": 2, 
            "price": 1505.50
        }
    }
    ```

## Error Handling

The tools will return a JSON object with an `"error"` key if an operation fails. The value will contain a descriptive message, often originating from the Kite Connect API itself (e.g., insufficient funds, invalid parameters, authentication errors).

## Development

*   **Adding More Tools**: To add more Kite Connect API functions (e.g., `get_holdings`, `get_positions`), define corresponding methods in `client.py`, create Pydantic models in `models.py` if needed, and register new tools in `main.py` using `@mcp.tool()`.
*   **Testing**: Requires a valid Kite Connect API key/secret and the ability to generate `request_token`s through the login flow.
