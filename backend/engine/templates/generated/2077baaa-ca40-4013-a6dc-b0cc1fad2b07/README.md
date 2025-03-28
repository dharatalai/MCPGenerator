# Jina AI DeepSearch MCP Server

This project provides a Model Context Protocol (MCP) server implementation for interacting with the [Jina AI DeepSearch API](https://jina.ai/deepsearch/). DeepSearch is an AI agent that combines web searching, reading, and reasoning to answer complex questions requiring up-to-date information or iterative investigation.

This server uses [FastMCP](https://github.com/datasette/fastmcp) (assuming this is the intended library, adjust if different) to expose the DeepSearch functionality as standardized tools.

## Features

*   Provides an MCP interface to Jina DeepSearch's chat completions endpoint.
*   Supports multimodal inputs (text, images, documents via data URIs).
*   Handles both streaming and non-streaming responses.
*   Configurable reasoning effort, token budget, domain filtering, and more.
*   Uses Pydantic for robust data validation.
*   Includes asynchronous API client using `httpx`.
*   Proper error handling and logging.

## Setup

1.  **Clone the repository (or create the files):**
    ```bash
    # If cloned from git
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

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Jina AI API key:
        ```dotenv
        JINA_API_KEY=your_jina_api_key_here
        ```
        You can obtain an API key from the [Jina AI platform](https://jina.ai/).
    *   You can also optionally set `HOST` and `PORT` in the `.env` file.

## Running the Server

You can run the MCP server using an ASGI server like Uvicorn:

```bash
uvicorn main:mcp --host 127.0.0.1 --port 8000 --reload
```

*   `--host`: The interface to bind to (e.g., `127.0.0.1` for local access, `0.0.0.0` for network access).
*   `--port`: The port to listen on.
*   `--reload`: Automatically restart the server when code changes (useful for development).

The server will start, and you can interact with it using an MCP client.

## Available Tools

### `chat_completion`

Performs a deep search and reasoning process based on a conversation history.

**Input:** `DeepSearchChatInput` model (see `models.py`)

*   `messages` (List[Message], required): Conversation history. Each message has a `role` ('user' or 'assistant') and `content` (string or list of `MessageContentItem` for multimodal).
*   `model` (str, optional, default: "jina-deepsearch-v1"): Model ID.
*   `stream` (bool, optional, default: `True`): Enable streaming. Highly recommended to avoid timeouts.
*   `reasoning_effort` (str, optional, default: 'medium'): 'low', 'medium', or 'high'.
*   `budget_tokens` (int, optional): Max tokens, overrides `reasoning_effort`.
*   `max_attempts` (int, optional): Max retries, overrides `reasoning_effort`.
*   `no_direct_answer` (bool, optional, default: `False`): Force search/thinking.
*   `max_returned_urls` (int, optional): Max URLs in the final answer.
*   `structured_output` (dict, optional): JSON schema for structured output.
*   `good_domains` (List[str], optional): Prioritized domains.
*   `bad_domains` (List[str], optional): Excluded domains.
*   `only_domains` (List[str], optional): Exclusively included domains.

**Output:** `Dict[str, Any]`

*   If `stream=False`, returns the complete JSON response from the API.
*   If `stream=True`, the server aggregates the streamed chunks and returns a final JSON object mimicking the non-streaming structure, including the full assistant message content, usage (if provided), finish reason, etc.
*   In case of errors, returns a dictionary with an `"error"` key containing details.

## Authentication

The server uses Bearer token authentication. The API key provided in the `.env` file (`JINA_API_KEY`) is automatically included in the `Authorization` header for requests to the Jina DeepSearch API.

## Rate Limits

The Jina DeepSearch API has rate limits (e.g., 10 requests per minute as per the plan). This MCP server implementation does *not* include client-side rate limiting. Ensure your usage patterns comply with Jina AI's limits.

## Error Handling

The server catches errors from the `httpx` client (network issues, timeouts) and HTTP status errors from the Jina API (e.g., 4xx, 5xx). It logs errors and returns a structured JSON error response to the MCP client.

## Example Usage (Conceptual MCP Client)

```python
import asyncio
from mcp.client.aio import AsyncMCPClient

async def main():
    client = AsyncMCPClient("http://127.0.0.1:8000") # URL of your running MCP server

    try:
        response = await client.jina_deepsearch.chat_completion(
            params={
                "messages": [
                    {"role": "user", "content": "What were the key announcements from Apple's latest WWDC?"}
                ],
                "stream": True, # Recommended
                "reasoning_effort": "medium"
            }
        )

        if "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("DeepSearch Response:")
            # Process the successful response dictionary
            print(response.get("choices", [{}])[0].get("message", {}).get("content"))
            print("--- Usage ---")
            print(response.get("usage"))

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```
