# Jina DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the Jina DeepSearch API using FastMCP.

Jina DeepSearch combines web searching, reading, and reasoning to answer complex questions that require iterative investigation, world-knowledge, or up-to-date information. This MCP server exposes its capabilities through a standardized tool interface.

## Features

*   **`chat_completion` Tool:** Provides access to the Jina DeepSearch `/v1/chat/completions` endpoint.
    *   Accepts conversation history (`messages`), including text and data URIs for images/documents.
    *   Supports streaming responses (default and recommended).
    *   Aggregates streamed responses into a single final result.
    *   Handles various parameters like `model`, `reasoning_effort`, domain filtering, structured output, etc.
    *   Compatible with the OpenAI Chat API schema.

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
    *   Edit the `.env` file:
        *   Add your Jina API key to `JINA_API_KEY`. You can obtain a key from [Jina AI](https://jina.ai/). While the API works without a key, it's heavily rate-limited (2 RPM). A standard key allows 10 RPM.
        *   The `JINA_DEEPSEARCH_BASE_URL` is usually not needed unless you are using a custom deployment.

## Running the Server

You can run the server using Uvicorn (recommended for development and production):

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes (useful for development).

Alternatively, you can run `python main.py`, which also uses Uvicorn internally but might offer less control.

The server will be available at `http://localhost:8000` (or the specified host/port).

## Authentication

The server uses Bearer token authentication for the Jina DeepSearch API. It reads the API key from the `JINA_API_KEY` environment variable specified in the `.env` file.

If no API key is provided, the API calls will be made without authentication, likely resulting in stricter rate limits (2 RPM).

## Tool Usage

An MCP client can interact with this server by calling the `jina_deepsearch.chat_completion` tool.

**Example MCP Client Request:**

```json
{
  "tool_name": "jina_deepsearch.chat_completion",
  "parameters": {
    "params": {
      "model": "jina-deepsearch-v1",
      "messages": [
        {"role": "user", "content": "What were the main announcements from Apple's latest WWDC event?"}
      ],
      "stream": true,
      "reasoning_effort": "medium"
    }
  }
}
```

**Expected MCP Server Response (Aggregated from Stream):**

```json
{
  "result": {
    "id": "chatcmpl-xxxx",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "jina-deepsearch-v1",
    "system_fingerprint": "fp_xxxx",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "Apple's latest WWDC event featured several key announcements including... [Full Answer] ... For more details, you can refer to the official Apple newsroom [1]."
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 25,
      "completion_tokens": 350,
      "total_tokens": 375
    },
    "visitedURLs": ["https://www.apple.com/newsroom/...", "https://www.techsite.com/..."],
    "readURLs": ["https://www.apple.com/newsroom/..."],
    "numURLs": 2,
    "aggregated_annotations": [
        {
            "type": "url_citation",
            "url_citation": {
                "url": "https://www.apple.com/newsroom/...",
                "title": "Apple Newsroom Article Title",
                "exactQuote": "Specific quote from the article."
            }
        }
    ]
  }
}
```

## Models

Pydantic models are used for type validation and serialization:

*   `DeepSearchChatParams`: Defines the input parameters for the `chat_completion` tool.
*   `DeepSearchResponse`: Defines the structure of the response from the Jina API (used for both chunks and final responses).
*   Other supporting models (`Message`, `Choice`, `Delta`, `Usage`, `Annotation`, `UrlCitation`) are defined in `models.py` based on the Jina API schema.

## Error Handling

The server includes error handling for:

*   **API Errors:** Catches `httpx.HTTPStatusError` (4xx, 5xx responses) from the Jina API and returns a JSON error message including the status code and API-provided details.
*   **Network Errors:** Catches `httpx.RequestError` (e.g., timeouts, connection issues) and returns a JSON error message.
*   **Validation Errors:** Pydantic models validate incoming parameters and outgoing responses.
*   **Unexpected Errors:** Generic exceptions are caught, logged, and returned as a JSON error message.

## Rate Limits

Be aware of the Jina DeepSearch API rate limits:

*   **No API Key:** 2 requests per minute (RPM)
*   **Standard API Key:** 10 RPM
*   **Premium API Key:** 100 RPM

Exceeding these limits will result in `429 Too Many Requests` errors.
