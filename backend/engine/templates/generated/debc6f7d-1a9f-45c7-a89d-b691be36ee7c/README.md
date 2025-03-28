# Jina DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the [Jina DeepSearch API](https://jina.ai/deepsearch/).

Jina DeepSearch is an AI service designed to answer complex questions by iteratively searching the web, reading content, and reasoning. It provides comprehensive answers with cited sources and is compatible with the OpenAI Chat API schema.

This MCP server exposes the Jina DeepSearch functionality as a tool, making it easy to integrate into applications using the MCP standard.

## Features

*   Provides a `chat_completion` tool to access Jina DeepSearch.
*   Supports both streaming (Server-Sent Events) and non-streaming responses.
*   Handles authentication using a Jina API key.
*   Includes Pydantic models for request inputs and response outputs.
*   Configurable via environment variables.
*   Built with [FastMCP](https://github.com/your-org/fastmcp). <!-- Replace with actual link if available -->

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Jina API key:
    ```env
    JINA_API_KEY="your_jina_api_key_here"
    ```
    You can obtain an API key from the [Jina AI Cloud](https://jina.ai/cloud/).

## Running the Server

You can run the MCP server using the `mcp` command-line tool (installed with `fastmcp`):

```bash
mcp run main:mcp
```

By default, it will run on `127.0.0.1:8000`. You can configure the host and port using environment variables (`MCP_HOST`, `MCP_PORT`) or command-line arguments:

```bash
mcp run main:mcp --host 0.0.0.0 --port 8080
```

## Tools

### `chat_completion`

Performs deep search and reasoning based on a conversation history.

**Description:**
Iteratively searches the web, reads content, and reasons to provide a comprehensive answer, citing sources. Suitable for complex questions requiring up-to-date information or multi-hop reasoning. Supports streaming responses for real-time updates.

**Input Parameters (`DeepSearchChatInput`):**

*   `messages` (List[`ChatMessage`], required): A list of messages comprising the conversation history. Each message has `role` ('user', 'assistant', 'system') and `content` (string or list for multimodal).
*   `model` (str, optional, default: `"jina-deepsearch-v1"`): ID of the model to use.
*   `stream` (bool, optional, default: `True`): Whether to stream back partial progress. Recommended to keep enabled.
*   `reasoning_effort` (Literal['low', 'medium', 'high'], optional, default: `"medium"`): Constrains effort on reasoning.
*   `budget_tokens` (int, optional): Maximum number of tokens allowed. Overrides `reasoning_effort`.
*   `max_attempts` (int, optional): Maximum number of retries. Overrides `reasoning_effort`.
*   `no_direct_answer` (bool, optional, default: `False`): Forces search steps even for trivial queries.
*   `max_returned_urls` (int, optional): Maximum number of URLs in the final answer.
*   `structured_output` (Dict[str, Any], optional): JSON schema to enforce on the output.
*   `good_domains` (List[str], optional): Domains to prioritize.
*   `bad_domains` (List[str], optional): Domains to exclude.
*   `only_domains` (List[str], optional): Domains to exclusively include.

**Returns:**

*   **If `stream=True`:** An `AsyncIterator[DeepSearchChunk]` yielding Server-Sent Events data parsed into `DeepSearchChunk` objects. The final chunk typically includes `usage` statistics and `visited_urls`.
*   **If `stream=False`:** A single `DeepSearchResponse` object containing the complete response, including `choices`, `usage`, and `visited_urls`.

**Example Usage (Conceptual MCP Client):**

```python
import mcp

async def main():
    client = mcp.Client("http://localhost:8000") # URL of the running MCP server

    # Non-streaming example
    response = await client.tools.jina_deepsearch.chat_completion(
        params={
            "messages": [
                {"role": "user", "content": "What were the key announcements at the latest Apple event?"}
            ],
            "stream": False
        }
    )
    print("Non-streaming response:", response)

    # Streaming example
    async for chunk in await client.tools.jina_deepsearch.chat_completion(
        params={
            "messages": [
                {"role": "user", "content": "Explain the concept of quantum entanglement simply."}
            ],
            "stream": True,
            "reasoning_effort": "low"
        }
    ):
        print("Stream chunk:", chunk)

# Run the example
# asyncio.run(main())
```

## Error Handling

The server attempts to catch common errors:

*   **Authentication Errors:** If `JINA_API_KEY` is invalid or missing.
*   **API Errors:** Errors returned by the Jina API (e.g., bad requests, server errors).
*   **Timeouts:** If the API request takes too long (especially for non-streaming requests).
*   **Connection Errors:** Network issues connecting to the Jina API.
*   **Validation Errors:** If input data is invalid or the API response doesn't match expected models.

Errors will be logged and generally result in an appropriate error response from the MCP server.

## Authentication

Authentication is handled via an API key (`JINA_API_KEY`) passed in the `Authorization: Bearer <key>` header to the Jina DeepSearch API. Ensure the `JINA_API_KEY` environment variable is set correctly when running the server.
