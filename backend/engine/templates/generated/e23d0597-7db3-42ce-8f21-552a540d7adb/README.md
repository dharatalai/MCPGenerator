# DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the Jina AI DeepSearch API using the FastMCP framework.

## Description

Jina AI's DeepSearch combines web searching, reading, and reasoning through iterative steps to provide comprehensive answers to complex questions, especially those requiring up-to-date information or multi-hop reasoning. It is fully compatible with the OpenAI Chat API schema.

This MCP server exposes the core functionality of DeepSearch through a single tool, allowing agents or applications to leverage its capabilities easily.

## Features

*   **`chat_completion` Tool:** Performs a deep search and reasoning process based on a conversation history.
    *   Supports standard chat messages (user, assistant, system).
    *   Handles optional parameters like `model`, `reasoning_effort`, `budget_tokens`, domain filtering, etc.
    *   Supports **streaming responses** (recommended for potentially long-running searches) via Server-Sent Events (SSE).
    *   Returns results compatible with the OpenAI Chat Completions API schema, including usage statistics and visited URLs.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment (recommended):**
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
        *   `JINA_API_KEY`: Add your Jina AI API key here. While optional (DeepSearch has a free tier with lower rate limits), it's highly recommended for production use or higher request volumes. You can obtain a key from [Jina AI Cloud](https://cloud.jina.ai/).

## Running the Server

You can run the MCP server using Uvicorn:

```bash
uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.
*   `--reload`: Automatically restarts the server when code changes (useful for development).

The server will be available at `http://localhost:8000` (or the specified host/port).

## Usage

You can interact with this MCP server using any MCP-compatible client, such as `mcp_client`.

**Example using `mcp_client` (Python):**

```python
from mcp_client import Client
import asyncio

async def main():
    client = Client(url="http://localhost:8000") # Adjust URL if needed

    # --- Non-Streaming Example ---
    print("--- Non-Streaming Request ---")
    params_no_stream = {
        "messages": [
            {"role": "user", "content": "What were the key announcements at the latest Apple event?"}
        ],
        "stream": False,
        "reasoning_effort": "low" # Faster response for simple queries
    }
    try:
        response = await client.arun_tool("chat_completion", params=params_no_stream)
        print("Response:", response)
        if isinstance(response, dict) and 'choices' in response:
            print("Answer:", response['choices'][0]['message']['content'])
            print("Visited URLs:", response.get('visited_urls'))
            print("Usage:", response.get('usage'))
    except Exception as e:
        print(f"Error: {e}")

    print("\
---")

    # --- Streaming Example ---
    print("--- Streaming Request ---")
    params_stream = {
        "messages": [
            {"role": "user", "content": "Compare the pros and cons of Next.js vs Remix for building web applications in 2024."}
        ],
        "stream": True
    }
    try:
        full_response_content = ""
        async for chunk in client.astream_tool("chat_completion", params=params_stream):
            print("Chunk:", chunk)
            if isinstance(chunk, dict) and 'choices' in chunk and chunk['choices']:
                delta = chunk['choices'][0].get('delta', {})
                content_piece = delta.get('content')
                if content_piece:
                    print(content_piece, end="", flush=True)
                    full_response_content += content_piece
        print("\
--- End of Stream ---")
        # Note: Usage and visited URLs often come in the *last* chunk in streaming

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

```

## Authentication

The server uses Bearer Token authentication if a `JINA_API_KEY` is provided in the environment variables. This key is passed in the `Authorization` header to the DeepSearch API.

## Error Handling

The server attempts to catch common errors:
*   **API Errors:** Errors returned by the DeepSearch API (e.g., 400 Bad Request, 401 Unauthorized, 429 Rate Limit Exceeded, 5xx Server Errors) are caught and returned as an MCP error response.
*   **Timeout Errors:** Requests taking too long (especially non-streaming ones) might time out.
*   **Network Errors:** Issues connecting to the DeepSearch API.
*   **Validation Errors:** Problems with the structure of the request or response.

Error responses are returned in the standard MCP format: `{"error": "Description of the error."}`.
