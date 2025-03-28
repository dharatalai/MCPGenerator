# Jina DeepSearch MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the [Jina AI DeepSearch API](https://jina.ai/deepsearch/).

Jina DeepSearch combines web searching, reading, and reasoning to provide comprehensive answers to complex questions. It's designed for tasks requiring iterative research, access to real-time information, and deep reasoning capabilities. The API is compatible with OpenAI's Chat API schema.

This MCP server exposes the core functionality of the DeepSearch API as a tool that can be easily integrated into agentic workflows or other applications supporting MCP.

## Features

*   Provides a `chat_completion` tool to access Jina DeepSearch.
*   Supports both streaming (Server-Sent Events) and non-streaming responses.
*   Handles authentication using Jina API keys.
*   Includes comprehensive Pydantic models for inputs and outputs.
*   Configurable via environment variables.
*   Built with [FastMCP](https://github.com/your-repo/fastmcp). <!-- Update link if available -->

## Prerequisites

*   Python 3.8+
*   A Jina AI API Key (obtain from [jina.ai/cloud](https://jina.ai/cloud/))

## Setup

1.  **Clone the repository (or create the files):**
    ```bash
    # If cloned from a repo:
    # git clone <repository-url>
    # cd <repository-directory>

    # If creating files manually, ensure you have main.py, models.py, api.py,
    # requirements.txt, and .env.example in the same directory.
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
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Jina API key:
        ```dotenv
        JINA_API_KEY=your_jina_api_key_here
        ```
    *   You can optionally override the API base URL or timeout in the `.env` file if needed.

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will start, typically on `http://127.0.0.1:8000` (check console output for the exact address).

## Available Tools

### `chat_completion`

Performs a deep search and reasoning process based on the provided conversation history and query.

**Parameters:**

*   `messages` (List[Message], **required**): A list of message objects, where each object has `role` ('user', 'assistant', 'system') and `content` (string, can be text or data URI).
*   `model` (str, optional): Model ID. Defaults to `jina-deepsearch-v1`.
*   `stream` (bool, optional): Whether to stream the response. Defaults to `True`.
*   `reasoning_effort` (str, optional): 'low', 'medium', or 'high'. Defaults to `medium`.
*   `budget_tokens` (int, optional): Max tokens for the process.
*   `max_attempts` (int, optional): Max retry attempts.
*   `no_direct_answer` (bool, optional): Force search/thinking. Defaults to `False`.
*   `max_returned_urls` (int, optional): Max URLs in the final answer.
*   `structured_output` (Dict[str, Any], optional): JSON schema for structured output.
*   `good_domains` (List[str], optional): Prioritized domains.
*   `bad_domains` (List[str], optional): Excluded domains.
*   `only_domains` (List[str], optional): Exclusively included domains.

**Returns:**

*   If `stream=True`: An asynchronous iterator yielding `DeepSearchChunk` objects.
*   If `stream=False`: A `DeepSearchResponse` object containing the complete answer, usage stats, and visited URLs.

**Example Usage (Conceptual MCP Client):**

```python
from mcp.client import MCPClient

async def main():
    client = MCPClient("http://127.0.0.1:8000") # Address where MCP server is running

    messages = [
        {"role": "user", "content": "What are the latest advancements in quantum computing resistant cryptography?"}
    ]

    # Non-streaming example
    # response = await client.call(
    #     tool_name="chat_completion",
    #     arguments={
    #         "messages": messages,
    #         "stream": False,
    #         "reasoning_effort": "high"
    #     }
    # )
    # print("Final Answer:", response['choices'][0]['message']['content'])
    # print("Visited URLs:", response.get('visited_urls'))
    # print("Usage:", response['usage'])

    # Streaming example
    async for chunk in await client.call_stream(
        tool_name="chat_completion",
        arguments={
            "messages": messages,
            "stream": True,
            "reasoning_effort": "medium"
        }
    ):
        if chunk['choices'] and chunk['choices'][0]['delta'] and chunk['choices'][0]['delta'].get('content'):
            print(chunk['choices'][0]['delta']['content'], end="", flush=True)
        # Final chunk might contain usage and visited_urls
        if chunk.get('usage'):
            print("\
--- Usage ---")
            print(chunk['usage'])
        if chunk.get('visited_urls'):
            print("\
--- Visited URLs ---")
            print(chunk['visited_urls'])

    await client.close()

# Run the example
# import asyncio
# asyncio.run(main())
```

## Error Handling

The server includes error handling for:

*   API authentication errors (missing or invalid API key).
*   Network errors (connection issues, timeouts).
*   API errors (4xx client errors, 5xx server errors from Jina API).
*   Invalid input or output data validation errors.

Errors originating from the API client or during processing within the tool will be logged and generally raised as exceptions, which the MCP client should handle.

## Rate Limits

The Jina DeepSearch API has rate limits (e.g., 10 requests per minute on free tiers). This MCP server does *not* implement client-side rate limiting. Ensure your usage patterns comply with the API's limits to avoid `429 Too Many Requests` errors.

## Development

*   **Code Structure:**
    *   `main.py`: MCP server setup and tool definitions.
    *   `api.py`: Client for interacting with the Jina DeepSearch API.
    *   `models.py`: Pydantic models for API requests and responses.
    *   `requirements.txt`: Python dependencies.
    *   `.env.example` / `.env`: Environment variable configuration.
*   **Linting/Formatting:** Consider using tools like `black` and `ruff` for code quality.
