# DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for the [Jina DeepSearch API](https://jina.ai/deepsearch/). It allows you to interact with DeepSearch using a standardized MCP interface, making it easy to integrate its advanced web search, content reading, and reasoning capabilities into applications compatible with MCP.

This server is built using [FastMCP](https://github.com/your-repo/fastmcp). <!-- Replace with actual FastMCP link if available -->

## Features

*   Provides an MCP interface for Jina DeepSearch's chat completions endpoint.
*   Supports text, image (data URI), and document (data URI) inputs.
*   Handles both streaming (Server-Sent Events) and non-streaming responses.
*   Configurable reasoning effort, token budgets, and domain filtering.
*   Built-in retry logic for transient network or server errors.
*   Authentication via Jina API Key.

## Prerequisites

*   Python 3.8+
*   A Jina API Key (optional but recommended for higher rate limits). Get one from [Jina AI Cloud](https://jina.ai/cloud/).

## Setup

1.  **Clone the repository (or create the files):**
    ```bash
    # If cloned from a repo:
    # git clone <repository-url>
    # cd <repository-directory>

    # If creating files manually, ensure you have:
    # main.py, models.py, api.py, requirements.txt, .env.example
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file by copying the example:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Jina API key:
    ```
    JINA_API_KEY=your_jina_api_key_here
    ```
    If you don't provide an API key, the service will still work but with significantly lower rate limits (2 requests per minute).

## Running the Server

Use an ASGI server like Uvicorn to run the application:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8000
```

Replace `8000` with your desired port.

The MCP server will now be running and accessible at `http://localhost:8000` (or the host/port you configured).

## Available Tools

The server exposes the following MCP tool:

### `chat_completion`

Performs a deep search and reasoning process based on conversation history.

**Input Parameters (`DeepSearchChatInput` model):**

*   `messages` (List[`Message`], required): Conversation history. See `Message` structure below.
*   `model` (str, optional, default: `jina-deepsearch-v1`): The model ID to use.
*   `stream` (bool, optional, default: `True`): Whether to stream results using Server-Sent Events. Highly recommended.
*   `reasoning_effort` (str, optional, default: `medium`): Controls reasoning depth ('low', 'medium', 'high').
*   `budget_tokens` (int, optional): Max tokens for the process (overrides `reasoning_effort`).
*   `max_attempts` (int, optional): Max reasoning retries (overrides `reasoning_effort`).
*   `no_direct_answer` (bool, optional, default: `False`): Force search/reasoning steps.
*   `max_returned_urls` (int, optional): Max URLs in the final answer.
*   `structured_output` (dict, optional): JSON schema for structured output.
*   `good_domains` (List[str], optional): Prioritized domains.
*   `bad_domains` (List[str], optional): Excluded domains.
*   `only_domains` (List[str], optional): Exclusively included domains.

**`Message` Structure:**

*   `role` (str, required): 'user' or 'assistant'.
*   `content` (Union[str, List[`MessageContentPart`]], required): Message content.

**`MessageContentPart` Structure (for multimodal content):**

*   `type` (str, required): 'text', 'image_url', or 'document_url'.
*   `text` (str, optional): Text content.
*   `image_url` (dict, optional): `{"url": "data:image/...;base64,..."}` (webp, png, jpeg).
*   `document_url` (dict, optional): `{"url": "data:application/pdf;base64,..."}` or `{"url": "data:text/plain;base64,..."}` (txt, pdf, max 10MB).

**Returns:**

*   If `stream=True`: An async generator yielding `DeepSearchResponseChunk` objects.
*   If `stream=False`: A single `DeepSearchResponse` object.

## Authentication

The server uses Bearer token authentication, expecting a Jina API key provided in the `JINA_API_KEY` environment variable. This key is automatically included in the `Authorization` header for requests to the DeepSearch API.

## Rate Limits

The Jina DeepSearch API has rate limits based on your API key:

*   **No Key:** 2 requests per minute (RPM)
*   **Standard Key:** 10 RPM
*   **Premium Key:** 100 RPM

The MCP server itself doesn't enforce these limits but relies on the underlying API. You may receive `429 Too Many Requests` errors if you exceed the limit associated with your key.

## Error Handling

The server attempts to handle common API errors:

*   **HTTP Errors (4xx, 5xx):** Logged and potentially raised as `DeepSearchAPIError`.
*   **Timeouts/Network Errors:** Retried automatically up to 3 times with exponential backoff.
*   **Invalid Responses:** Logged, and may result in errors.

## Example Usage (using `mcp client`)

Assuming the server is running on `http://localhost:8000`:

**Non-streaming:**

```bash
mcp client call http://localhost:8000 chat_completion \\
  params='{
    "messages": [{"role": "user", "content": "What were the main outcomes of the COP28 conference?"}],
    "stream": false
  }'
```

**Streaming:**

```bash
mcp client call http://localhost:8000 chat_completion \\
  params='{
    "messages": [{"role": "user", "content": "Explain the theory of relativity simply."}],
    "stream": true
  }'
```

*(Note: `mcp client` might need specific flags or handling for streaming output depending on its implementation.)*
