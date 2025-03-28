# Jina AI DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the Jina AI DeepSearch API using FastMCP.

## Description

The Jina AI DeepSearch API provides advanced search capabilities by combining web searching, reading, and reasoning to answer complex questions. This MCP server exposes the DeepSearch functionality through a standardized tool interface, making it easy to integrate into MCP-compatible applications and agents.

The server is designed to be compatible with the OpenAI Chat API schema for inputs and outputs.

## Features

*   **`chat_completion` Tool:**
    *   Performs a deep search and reasoning process based on a conversation history.
    *   Supports streaming responses (Server-Sent Events) for real-time updates (recommended).
    *   Supports non-streaming responses (single JSON object).
    *   Configurable parameters like `model`, `reasoning_effort`, `max_attempts`, domain filtering, and structured output.

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
    *   Edit the `.env` file and add your Jina AI API key:
        ```dotenv
        JINA_API_KEY=your_jina_api_key_here
        ```
    *   You can also optionally set `DEEPSEARCH_BASE_URL` and `PORT` in the `.env` file.

## Running the Server

You can run the MCP server using Uvicorn:

```bash
# Basic run
uvicorn main:mcp.app

# Run with auto-reload (for development)
uvicorn main:mcp.app --reload

# Specify host and port
uvicorn main:mcp.app --host 0.0.0.0 --port 8000
```

The server will start, and you should see log output indicating it's running.

## Usage

Once the server is running, you can interact with it using any MCP client or standard HTTP requests.

**Example Request (using `curl`):**

This example calls the `chat_completion` tool with streaming enabled.

```bash
curl -X POST http://localhost:8000/tools/chat_completion/invoke \\
-H "Content-Type: application/json" \\
-d '{
  "params": {
    "messages": [
      {"role": "user", "content": "What were the main causes of the French Revolution?"}
    ],
    "model": "jina-deepsearch-v1",
    "stream": true,
    "reasoning_effort": "medium"
  }
}' --no-buffer
```

**Expected Response (Streaming):**

You will receive a stream of Server-Sent Events (SSE). Each event's `data` field will contain a JSON object representing a `DeepSearchChatCompletionChunk`.

```text
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1700000000,"model":"jina-deepsearch-v1","choices":[{"delta":{"role":"assistant"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1700000000,"model":"jina-deepsearch-v1","choices":[{"delta":{"content":"The main causes..."},"index":0,"finish_reason":null}]}

...

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1700000000,"model":"jina-deepsearch-v1","choices":[{"delta":{},"index":0,"finish_reason":"stop"}], "usage": {"prompt_tokens": 15, "completion_tokens": 250, "total_tokens": 265}}

data: [DONE]
```

**Example Request (Non-Streaming):**

```bash
curl -X POST http://localhost:8000/tools/chat_completion/invoke \\
-H "Content-Type: application/json" \\
-d '{
  "params": {
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "stream": false
  }
}'
```

**Expected Response (Non-Streaming):**

A single JSON object representing the complete `DeepSearchChatCompletion`.

```json
{
  "result": {
    "id": "chatcmpl-yyy",
    "object": "chat.completion",
    "created": 1700000010,
    "model": "jina-deepsearch-v1",
    "choices": [
      {
        "message": {
          "role": "assistant",
          "content": "The capital of France is Paris."
        },
        "index": 0,
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 6,
      "total_tokens": 16
    }
  }
}
```

## Authentication

This server requires a Jina AI API key for authentication. Ensure the `JINA_API_KEY` environment variable is set correctly in your `.env` file.

## Error Handling

The server includes error handling for common issues:

*   **Authentication Errors (401/403):** Invalid or missing API key.
*   **Rate Limit Errors (429):** Exceeded API request limits.
*   **Bad Request Errors (400):** Invalid input parameters or message format.
*   **Timeout Errors:** Request took too long to complete.
*   **Server Errors (5xx):** Issues on the Jina AI DeepSearch API side.
*   **Network Errors:** Problems connecting to the API.

Errors will be logged, and the API tool will typically return a JSON object containing an `"error"` key and a descriptive message.
