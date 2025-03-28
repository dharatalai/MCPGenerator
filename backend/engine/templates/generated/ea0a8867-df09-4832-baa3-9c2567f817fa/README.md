# DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for the Jina AI DeepSearch API, built using FastMCP.

## Description

The Jina AI DeepSearch API combines web searching, reading, and reasoning capabilities to answer complex questions that require up-to-date information or iterative investigation. It is designed to be compatible with the OpenAI Chat API schema.

This MCP server provides a standardized interface to access the DeepSearch API's `chat_completion` functionality.

## Features

*   Provides the `chat_completion` tool via MCP.
*   Supports all parameters of the DeepSearch API endpoint (`model`, `messages`, `stream`, `reasoning_effort`, domain filtering, etc.).
*   Handles both streaming and non-streaming responses from the API.
*   Includes robust error handling for API errors, timeouts, and network issues.
*   Uses Pydantic for request and response validation.
*   Requires a Jina AI API key for authentication.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment:**
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
    *   Edit the `.env` file and add your Jina AI API key:
        ```env
        JINA_API_KEY="YOUR_JINA_API_KEY_HERE"
        ```
        You can obtain an API key from the [Jina AI Cloud Dashboard](https://jina.ai/cloud/).

## Running the Server

Use `uvicorn` to run the FastMCP application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on (default for FastMCP is often 8000).
*   `--reload`: Enables auto-reloading when code changes (useful for development).

The MCP server will be available at `http://localhost:8000` (or the specified host/port).

## Available Tools

### `chat_completion`

Performs a deep search and reasoning process to answer a user query based on web search results and iterative thinking.

**Input Parameters (as a JSON object matching `DeepSearchChatParams`):**

*   `messages` (List[Message], **required**): A list of message objects representing the conversation history. Each message has `role` ('user' or 'assistant') and `content` (string or list for multimodal).
*   `model` (str, **required**): Model ID. Defaults to `jina-deepsearch-v1`.
*   `stream` (bool, optional): Whether to stream results. Defaults to `true`. Note: While the API supports streaming, this MCP tool consumes the stream and returns a single aggregated response when `stream=true`.
*   `reasoning_effort` (str, optional): 'low', 'medium', or 'high'. Defaults to `medium`.
*   `budget_tokens` (int, optional): Max tokens for the process. Overrides `reasoning_effort`.
*   `max_attempts` (int, optional): Max retries for solving. Overrides `reasoning_effort`.
*   `no_direct_answer` (bool, optional): Force search/thinking even for simple queries. Defaults to `false`.
*   `max_returned_urls` (int, optional): Max URLs in the final answer.
*   `structured_output` (Dict, optional): JSON schema for structured output.
*   `good_domains` (List[str], optional): Prioritized domains.
*   `bad_domains` (List[str], optional): Excluded domains.
*   `only_domains` (List[str], optional): Exclusively included domains.

**Returns (JSON object):**

*   If `stream=false`, returns the standard Chat Completion JSON response from the API.
*   If `stream=true`, returns an aggregated JSON response mimicking the non-streaming structure, containing the complete message content, final usage statistics, finish reason, and potentially DeepSearch-specific metadata like URLs visited/read.

## Authentication

The server uses Bearer Token authentication. The Jina AI API key provided in the `.env` file (`JINA_API_KEY`) is automatically included in the `Authorization` header for requests to the DeepSearch API.

## Error Handling

The server attempts to catch common errors:

*   **Authentication Errors (401):** If the API key is invalid or missing.
*   **Rate Limit Errors (429):** If the API rate limit is exceeded.
*   **Invalid Request Errors (400):** If the input parameters are invalid.
*   **Server Errors (5xx):** If the DeepSearch API encounters an internal error.
*   **Timeout Errors:** If the request takes longer than the configured timeout (default 120s).
*   **Network Errors:** If there's trouble connecting to the API.

Errors are returned as a JSON object with `error` and `status_code` fields.

## Rate Limits

Be aware of the Jina AI DeepSearch API rate limits associated with your API key:
*   **Free Key:** ~2 requests per minute (RPM)
*   **Standard Key:** ~10 RPM
*   **Premium Key:** ~100 RPM

The client currently does not implement automatic retries or backoff for rate limits, but will return a 429 error.
