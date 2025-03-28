# Jina DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the Jina DeepSearch API using FastMCP.

Jina DeepSearch is an AI agent designed to answer complex questions by combining web searching, reading, and reasoning capabilities. This MCP server exposes its functionality through a standard interface compatible with the OpenAI Chat API schema.

## Features

*   Provides access to Jina DeepSearch via the `chat_completion` tool.
*   Handles conversation history, including multimodal inputs (text, images, documents via data URIs).
*   Supports various parameters to control reasoning effort, token budget, domain filtering, and more.
*   Manages API authentication using a Jina API key.
*   Handles API streaming internally and returns the final aggregated response.
*   Includes error handling, logging, and proper request/response modeling using Pydantic.

## Service Name

`jina_deepsearch`

## Tools

### 1. `chat_completion`

*   **Description**: Performs a deep search and reasoning process based on a conversation history to generate a comprehensive answer. Suitable for complex questions requiring iterative research, world-knowledge, or up-to-date information. Handles streaming internally and returns the final aggregated response.
*   **Input**: `DeepSearchChatParams` (See `models.py` for details)
    *   `messages` (List[Message], **required**): Conversation history. Each message has `role` ('user' or 'assistant') and `content` (string or list of `MessageContentPart` for multimodal).
    *   `model` (str, optional, default: `jina-deepsearch-v1`): Model ID.
    *   `reasoning_effort` (str, optional, default: `medium`): 'low', 'medium', or 'high'.
    *   `budget_tokens` (int, optional): Max tokens for the process.
    *   `max_attempts` (int, optional): Max reasoning retries.
    *   `no_direct_answer` (bool, optional, default: `false`): Force search steps.
    *   `max_returned_urls` (int, optional): Max URLs in the final answer.
    *   `structured_output` (Any, optional): JSON schema for structured output.
    *   `good_domains` (List[str], optional): Prioritized domains.
    *   `bad_domains` (List[str], optional): Excluded domains.
    *   `only_domains` (List[str], optional): Exclusively included domains.
    *   `stream` (bool): Although present in the model, the tool forces this to `true` internally for API calls and handles aggregation. The client should not set this.
*   **Returns**: `ChatCompletionResponse` (Dictionary, see `models.py` for details)
    *   `id` (str): Unique completion ID.
    *   `object` (str): 'chat.completion'.
    *   `created` (int): Timestamp.
    *   `model` (str): Model used.
    *   `choices` (List[Choice]): List containing the generated message (`ResponseMessage` with `role`, `content`, `annotations`) and `finish_reason`.
    *   `usage` (Usage): Token usage statistics.
    *   `visited_urls` (List[str], optional): URLs visited.
    *   `read_urls` (List[str], optional): URLs read.

## Authentication

This server requires a Jina AI API key.

1.  Obtain an API key from [Jina AI Cloud](https://jina.ai/cloud/).
2.  Set the `JINA_API_KEY` environment variable.

The server reads this key from the environment and includes it as a Bearer token in the `Authorization` header for all requests to the Jina DeepSearch API.

## Setup

1.  **Clone the repository (or save the generated files):**
    ```bash
    # If you have the files locally
    cd /path/to/your/project
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

4.  **Configure environment variables:**
    *   Create a `.env` file in the project root directory.
    *   Copy the contents of `.env.example` into `.env`.
    *   Replace `your_jina_api_key_here` with your actual Jina API key.
    ```env
    # .env
    JINA_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # Optional:
    # LOG_LEVEL=DEBUG
    # PORT=8080
    ```

## Running the Server

Use Uvicorn to run the ASGI application defined in `main.py`:

```bash
uvicorn main:mcp.app --host 0.0.0.0 --port 8080 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8080`: Specifies the port (defaults to 8080 if `PORT` env var is not set).
*   `--reload`: Automatically restarts the server when code changes (useful for development).

The server will start, and you can interact with it using an MCP client at `http://localhost:8080` (or the appropriate host/port).

## Example Usage (Conceptual MCP Client)

```python
import mcp.client

async def main():
    # Connect to the running MCP server
    client = mcp.client.Client("http://localhost:8080")

    try:
        response = await client.tools.jina_deepsearch.chat_completion(
            params={
                "messages": [
                    {"role": "user", "content": "What were the main announcements from the latest Apple event regarding the Vision Pro?"}
                ],
                "reasoning_effort": "high"
            }
        )

        print("Jina DeepSearch Response:")
        print(response)

        # Access specific parts
        if response and not response.get('error'):
            answer = response.get('choices', [{}])[0].get('message', {}).get('content')
            print("\
Answer:", answer)
            usage = response.get('usage')
            print("\
Usage:", usage)
            citations = response.get('choices', [{}])[0].get('message', {}).get('annotations')
            if citations:
                print("\
Citations:")
                for anno in citations:
                    if anno.get('type') == 'url_citation' and anno.get('url_citation'):
                        print(f"- {anno['url_citation'].get('title')}: {anno['url_citation'].get('url')}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Note:** The exact client usage depends on the specific MCP client library implementation.
