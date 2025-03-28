# DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for Jina AI's DeepSearch API, built using FastMCP.

DeepSearch combines web searching, reading, and reasoning for comprehensive investigation. It provides answers to complex questions requiring iterative reasoning, world-knowledge, or up-to-date information. The API is compatible with the OpenAI Chat API schema.

This MCP server exposes the DeepSearch chat completion functionality as a standardized tool.

## Features

*   **Chat Completion:** Provides access to the core DeepSearch `/v1/chat/completions` endpoint.
*   **Streaming Support:** Handles Server-Sent Events (SSE) for real-time responses when `stream=True`.
*   **Configurable Parameters:** Supports various DeepSearch parameters like `reasoning_effort`, `budget_tokens`, domain filtering, structured output, etc.
*   **OpenAI Schema Compatible:** Uses input and output models largely compatible with the OpenAI API schema.
*   **Error Handling:** Includes handling for API errors, network issues, timeouts, and validation errors.
*   **Async Implementation:** Built with `asyncio`, `httpx`, and `FastMCP` for efficient asynchronous operations.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\\Scripts\\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    *   Copy the example `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Jina AI API key:
        ```env
        JINA_API_KEY=your_jina_api_key_here
        # LOG_LEVEL=DEBUG # Optional: Set to DEBUG for more verbose logs
        ```
        You can obtain a Jina AI API key from [Jina AI Cloud](https://jina.ai/cloud/).

## Running the Server

Use Uvicorn to run the FastMCP application:

```bash
# For development with auto-reload
uvicorn main:mcp.app --reload --host 0.0.0.0 --port 8000

# For production (adjust workers as needed)
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --workers 4
```

The MCP server will be available at `http://localhost:8000`.

*   **MCP Schema:** `http://localhost:8000/mcp/schema`
*   **Tool Execution:** `http://localhost:8000/mcp/run/{tool_name}` (POST request)
*   **OpenAPI Docs (FastAPI):** `http://localhost:8000/docs`

## Environment Variables

*   `JINA_API_KEY` (Required): Your Jina AI API key.
*   `DEEPSEARCH_BASE_URL` (Optional): Overrides the default DeepSearch API base URL (`https://deepsearch.jina.ai`).
*   `LOG_LEVEL` (Optional): Sets the application's logging level (e.g., `INFO`, `DEBUG`). Defaults to `INFO`.

## Tools

### `chat_completion`

Performs a chat completion request using the DeepSearch engine.

*   **Description:** This involves iterative search, reading, and reasoning to find the best answer to the user's query, especially for complex questions requiring up-to-date information or deep research.
*   **Input:** Accepts parameters defined by the `DeepSearchChatParams` model (see `models.py`). Key parameters include:
    *   `messages`: List of conversation messages (user/assistant roles).
    *   `model`: Model ID (defaults to `jina-deepsearch-v1`).
    *   `stream`: Boolean, enables SSE streaming (defaults to `True`).
    *   `reasoning_effort`, `budget_tokens`, `max_attempts`: Control reasoning complexity.
    *   `max_returned_urls`, `good_domains`, `bad_domains`, `only_domains`: Control source retrieval.
    *   `structured_output`: Enforce a JSON schema on the output.
*   **Output:**
    *   If `stream=False`: Returns a JSON object matching the `DeepSearchChatResponse` model (see `models.py`), containing the final answer, usage stats, and citations.
    *   If `stream=True`: Returns an asynchronous stream of JSON objects, each matching the `DeepSearchChatStreamResponse` model, representing chunks of the response.

## Authentication

The server uses an API Key (Bearer Token) for authenticating with the Jina AI DeepSearch API. The key is read from the `JINA_API_KEY` environment variable and included in the `Authorization` header of outgoing requests.

## Error Handling

The server attempts to handle various errors:

*   **HTTP Errors:** Catches 4xx and 5xx responses from the DeepSearch API.
*   **Timeouts:** Handles request timeouts.
*   **Network Errors:** Catches connection issues.
*   **Validation Errors:** Validates input parameters and API responses against Pydantic models.
*   **Configuration Errors:** Checks for the presence of the API key on startup.

Error details are logged, and an error message is returned to the MCP client, typically in a `{"error": "..."}` format.

## Rate Limits

The DeepSearch API has rate limits (e.g., 10 requests per minute on free tiers, check Jina AI documentation for details). This MCP server implementation **does not** currently enforce these rate limits on incoming requests. Clients calling this MCP server should implement their own rate-limiting logic if necessary to avoid hitting the upstream API limits.

## Dependencies

*   `fastmcp`: The MCP server framework.
*   `httpx`: Asynchronous HTTP client.
*   `pydantic`: Data validation and settings management.
*   `python-dotenv`: Loading environment variables from `.env` files.
*   `uvicorn`: ASGI server to run the application.
