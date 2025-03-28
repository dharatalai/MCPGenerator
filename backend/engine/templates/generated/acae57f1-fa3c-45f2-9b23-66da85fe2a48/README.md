# Jina AI DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for the [Jina AI DeepSearch API](https://jina.ai/deepsearch/). DeepSearch combines web searching, reading, and reasoning to provide comprehensive answers to complex questions, offering an API compatible with the OpenAI Chat API schema.

This server is built using [FastMCP](https://github.com/cognita-ai/fastmcp).

## Features

*   Provides an MCP interface to the Jina DeepSearch `/v1/chat/completions` endpoint.
*   Supports both streaming and non-streaming responses.
*   Handles complex input including text, images (data URI), and files (data URI).
*   Configurable reasoning effort, token budgets, domain filtering, and more.
*   Built-in Pydantic models for request and response validation.
*   Asynchronous API client using `httpx`.
*   Authentication via Bearer token (API Key).

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
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Jina AI API key:
    ```env
    JINA_API_KEY=your_jina_api_key_here
    # JINA_DEEPSEARCH_BASE_URL=https://deepsearch.jina.ai # Optional override
    ```
    You can obtain an API key from the [Jina AI website](https://jina.ai/).

## Running the Server

Use `uvicorn` to run the ASGI application:

```bash
# Basic execution
uvicorn main:mcp.app --host 0.0.0.0 --port 8000

# With auto-reload for development
uvicorn main:mcp.app --reload --port 8000
```

The MCP server will be available at `http://localhost:8000`.

## Available Tools

### `chat_completions`

Generates a response based on iterative search, reading, and reasoning using Jina DeepSearch.

**Description:** Corresponds to the `/v1/chat/completions` endpoint of the Jina DeepSearch API.

**Input:** `DeepSearchChatRequest` model

*   `messages` (List[Message], required): Conversation history. Messages can contain text, `image_url` (data URI), or `file_url` (data URI for txt/pdf up to 10MB).
*   `model` (str, optional, default: "jina-deepsearch-v1"): Model ID.
*   `stream` (bool, optional, default: True): Enable streaming response. **Strongly recommended** to avoid timeouts.
*   `reasoning_effort` (str, optional, default: "medium"): Control reasoning ('low', 'medium', 'high').
*   `budget_tokens` (int, optional): Max token budget.
*   `max_attempts` (int, optional): Max retry attempts.
*   `no_direct_answer` (bool, optional, default: False): Force search even for trivial questions.
*   `max_returned_urls` (int, optional): Max URLs in the final answer.
*   `structured_output` (dict, optional): JSON schema for structured output.
*   `good_domains` (List[str], optional): Prioritized domains.
*   `bad_domains` (List[str], optional): Excluded domains.
*   `only_domains` (List[str], optional): Exclusively included domains.

**Output:**

*   If `stream=True`: An `AsyncGenerator` yielding `DeepSearchChatChunk` objects.
*   If `stream=False`: A single `DeepSearchChatResponse` object.

**Authentication:** Requires the `JINA_API_KEY` environment variable to be set for Bearer token authentication.

**Rate Limits:** The Jina DeepSearch API has rate limits (e.g., 10 requests/minute). This server does not implement explicit rate limiting; ensure your usage complies with Jina AI's terms.

**Error Handling:** The tool propagates errors from the API, including HTTP status errors (4xx, 5xx), network errors, and validation errors.

## Example Usage (Conceptual MCP Client)

```python
from mcp.client.fastmcp import FastMCPClient

async def main():
    client = FastMCPClient(base_url="http://localhost:8000")

    request_data = {
        "messages": [
            {"role": "user", "content": "What were the key advancements in AI in 2023?"}
        ],
        "stream": True,
        "reasoning_effort": "medium"
    }

    try:
        # Streaming example
        async for chunk in await client.tools.jina_deepsearch.chat_completions(request=request_data):
            # Process each chunk (e.g., print content delta)
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
            # Final chunk might contain usage, visitedURLs etc.
            if chunk.usage:
                print(f"\
\
Usage: {chunk.usage}")
                print(f"Visited URLs: {chunk.visitedURLs}")

        # Non-streaming example
        # request_data["stream"] = False
        # response = await client.tools.jina_deepsearch.chat_completions(request=request_data)
        # print(response.choices[0].message.content)
        # print(response.usage)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```
