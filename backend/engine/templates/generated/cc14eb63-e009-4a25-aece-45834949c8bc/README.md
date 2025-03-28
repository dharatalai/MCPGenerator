# Jina AI DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the Jina AI DeepSearch API using FastMCP.

## Description

Jina AI DeepSearch provides advanced search, reading, and reasoning capabilities. It acts as an autonomous agent that iteratively searches the web, reads content, and reasons to find the best answer for complex queries requiring up-to-date information or multi-hop reasoning. This MCP server exposes the DeepSearch functionality through a standardized tool interface, fully compatible with the OpenAI Chat API schema.

## Features

*   Integrates with Jina AI DeepSearch API (`/v1/chat/completions`).
*   Supports both streaming and non-streaming responses.
*   Handles multi-modal inputs (text, images via data URI, files via data URI).
*   Provides comprehensive configuration options for the search and reasoning process.
*   Includes robust error handling and logging.
*   Manages API key authentication.

## Tools

### `chat_completion`

Performs a deep search and reasoning process based on a conversation history.

**Input Parameters:**

*   `messages` (List[Dict]): Conversation history. Each dict must have `role` ('user' or 'assistant') and `content`. `content` can be a string or a list of content parts (see below). (Required)
    *   Text Part: `{"type": "text", "text": "..."}`
    *   Image Part: `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}`
    *   File Part: `{"type": "file_url", "file_url": {"url": "data:application/pdf;base64,..."}}`
*   `model` (str): Model ID (default: `jina-deepsearch-v1`).
*   `stream` (bool): Enable streaming response (default: `True`). Recommended for long queries.
*   `reasoning_effort` (str): Reasoning effort ('low', 'medium', 'high', default: `medium`).
*   `budget_tokens` (int, optional): Max tokens for the process.
*   `max_attempts` (int, optional): Max retries with different approaches.
*   `no_direct_answer` (bool): Force search/thinking steps (default: `False`).
*   `max_returned_urls` (int, optional): Max URLs in the final response.
*   `structured_output` (Dict, optional): JSON schema for the final answer.
*   `good_domains` (List[str], optional): Prioritized domains.
*   `bad_domains` (List[str], optional): Excluded domains.
*   `only_domains` (List[str], optional): Exclusive domains.

**Returns:**

*   If `stream=True`: An asynchronous iterator yielding JSON objects representing `DeepSearchChatResponseChunk`.
*   If `stream=False`: A JSON object representing `DeepSearchChatResponse`.

(See `models.py` for the detailed structure of response objects).

## Authentication

The server uses an API Key for authentication with the Jina AI API.

1.  Obtain an API key from [Jina AI](https://jina.ai/).
2.  Set the `JINA_API_KEY` environment variable.

An API key is recommended for higher rate limits (10 RPM standard vs 2 RPM free). Premium keys offer 100 RPM. New keys typically come with 1 million free tokens.

## Setup

1.  **Clone the repository (or create files):**
    ```bash
    # If cloned
    # git clone <repository_url>
    # cd <repository_directory>
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

4.  **Configure environment variables:**
    *   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Jina AI API key:
        ```
        JINA_API_KEY=your_jina_api_key_here
        ```

## Running the Server

```bash
python main.py
```

By default, the server will run on `http://127.0.0.1:8000`. You can configure the host and port using environment variables (`HOST`, `PORT`) or by modifying the `mcp.run()` call in `main.py`.

## Usage Example (Conceptual MCP Client)

```python
import mcp
import asyncio

async def main():
    client = mcp.Client("http://127.0.0.1:8000") # URL of your running MCP server

    # Non-streaming example
    response = await client.tools.jina_deepsearch.chat_completion(
        messages=[{"role": "user", "content": "What were the key announcements at the latest Apple event?"}],
        stream=False,
        max_returned_urls=3
    )
    print("--- Non-Streaming Response ---")
    print(response)

    # Streaming example
    print("\
--- Streaming Response ---")
    async for chunk in await client.tools.jina_deepsearch.chat_completion(
        messages=[{"role": "user", "content": "Compare the performance of Llama 3 and GPT-4o on coding tasks."}],
        stream=True
    ):
        print(chunk)

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

The server attempts to catch common errors:

*   **HTTP Errors:** 4xx (e.g., 400 Bad Request, 401 Unauthorized, 429 Too Many Requests) and 5xx (e.g., 500 Internal Server Error, 504 Gateway Timeout) from the Jina API are logged and potentially returned as errors in the MCP response.
*   **Network Errors:** Timeouts or connection issues are caught and logged.
*   **Validation Errors:** Issues with the structure of the API response are logged.
*   **Input Errors:** Invalid input to the tool (e.g., malformed messages) might be caught by Pydantic validation.

Check the server logs for detailed error information.

## Rate Limits

Be mindful of Jina AI's rate limits:

*   **Free Tier:** 2 requests per minute (RPM)
*   **Standard Key:** 10 RPM
*   **Premium Key:** 100 RPM

Limits are applied per API key. Exceeding limits will result in `429 Too Many Requests` errors.
