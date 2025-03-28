# Jina DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for the Jina AI DeepSearch API, built using FastMCP.

The Jina DeepSearch API allows users to perform complex search queries that require iterative reasoning, web searching, and reading to find the best answer. It is designed for complex questions needing world knowledge or up-to-date information and is compatible with the OpenAI Chat API schema.

This MCP server exposes the DeepSearch functionality as standardized tools that can be easily integrated into agentic workflows or other applications.

## Features

*   **Chat Completion:** Provides access to the core DeepSearch chat completion endpoint.
*   **Streaming Support:** Handles streaming responses (`stream=True`) for real-time updates and reasoning steps, crucial for avoiding timeouts on complex queries.
*   **Parameter Control:** Supports various DeepSearch parameters like `reasoning_effort`, `budget_tokens`, `max_attempts`, domain filtering (`good_domains`, `bad_domains`, `only_domains`), and `structured_output`.
*   **Async Implementation:** Built with `asyncio` and `httpx` for efficient asynchronous operations.
*   **Pydantic Models:** Uses Pydantic for robust data validation and clear schema definitions.
*   **Configuration:** Easily configurable via environment variables.
*   **Error Handling:** Includes error handling for API issues, timeouts, and validation errors.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
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
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Jina AI API key:
    ```env
    JINA_API_KEY="your_jina_api_key_here"

    # Optional: Adjust other settings if needed
    # MCP_TIMEOUT=180
    # LOG_LEVEL=INFO
    ```
    You can obtain a Jina API key from [Jina AI Cloud](https://jina.ai/cloud/).

## Running the Server

You can run the MCP server using Uvicorn:

```bash
# Basic execution with auto-reload (for development)
uvicorn main:mcp --reload

# Specify host and port
uvicorn main:mcp --host 0.0.0.0 --port 8080
```

The server will start, and you can interact with it using an MCP client or tools like `curl`.

## Environment Variables

*   `JINA_API_KEY` (Required): Your Jina AI API key.
*   `DEEPSEARCH_API_BASE_URL` (Optional): Override the default API base URL (`https://deepsearch.jina.ai`).
*   `MCP_TIMEOUT` (Optional): Timeout in seconds for API requests (default: 180).
*   `LOG_LEVEL` (Optional): Logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`) (default: `INFO`).
*   `HOST` (Optional): Host address for the server (default: `127.0.0.1`).
*   `PORT` (Optional): Port for the server (default: `8000`).

## Tools

### `chat_completion`

Executes a chat completion request using the DeepSearch engine.

**Input Schema:** (`models.DeepSearchChatInput`)

*   `messages` (List[`Message`], required): Conversation history.
*   `model` (str, optional, default: `jina-deepsearch-v1`): Model ID.
*   `stream` (bool, optional, default: `True`): Enable streaming.
*   `reasoning_effort` (str, optional, default: `medium`): Reasoning effort (`low`, `medium`, `high`).
*   `budget_tokens` (int, optional): Max tokens budget.
*   `max_attempts` (int, optional): Max solution attempts.
*   `no_direct_answer` (bool, optional, default: `False`): Force search steps.
*   `max_returned_urls` (int, optional): Max URLs in response.
*   `structured_output` (dict, optional): JSON schema for output.
*   `good_domains` (List[str], optional): Prioritized domains.
*   `bad_domains` (List[str], optional): Excluded domains.
*   `only_domains` (List[str], optional): Exclusively included domains.

**Returns:**

*   If `stream=False`: A dictionary representing the full chat completion result (`models.DeepSearchChatOutput`).
*   If `stream=True`: An asynchronous generator yielding dictionaries for each chunk (`models.DeepSearchChatChunk`).

## Authentication

The server uses API Key authentication. The Jina API key must be provided via the `JINA_API_KEY` environment variable. The client includes this key in the `Authorization: Bearer <key>` header for requests to the DeepSearch API.

## Error Handling

The server catches common errors:

*   **HTTP Errors:** 4xx and 5xx errors from the DeepSearch API.
*   **Connection Errors:** Issues connecting to the API.
*   **Timeout Errors:** Requests taking longer than the configured `MCP_TIMEOUT`.
*   **Validation Errors:** Issues with input data or unexpected API response formats.

Errors are logged, and FastMCP will typically return a standardized error response to the client.

## Rate Limits

Be mindful of the Jina DeepSearch API rate limits associated with your API key:

*   **Free Tier:** 2 requests per minute (RPM)
*   **Standard Tier:** 10 RPM
*   **Premium Tier:** 100 RPM

Exceeding these limits will result in HTTP 429 errors.
