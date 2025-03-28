# Jina AI DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server implementation for interacting with the Jina AI DeepSearch API using the FastMCP framework.

## Description

Jina AI DeepSearch combines web searching, reading, and reasoning capabilities to perform comprehensive investigations into complex questions. It functions as an agent that iteratively researches topics to provide accurate and well-supported answers. The DeepSearch API is designed to be compatible with the OpenAI Chat API schema.

This MCP server exposes the core functionality of the DeepSearch API as a tool, allowing agents or applications to leverage its advanced search and reasoning capabilities through the MCP standard.

## Features

*   Provides an MCP interface to the Jina AI DeepSearch `/v1/chat/completions` endpoint.
*   Supports both standard (non-streaming) and streaming responses.
*   Handles authentication using Jina AI API keys.
*   Includes robust error handling for API and network issues.
*   Uses Pydantic models for clear data validation and structure.
*   Configurable via environment variables.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment:**
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
    *   Edit the `.env` file and add your Jina AI API key:
        ```dotenv
        JINA_API_KEY="your_jina_api_key_here"
        ```
        You can obtain an API key from the [Jina AI Platform](https://jina.ai/).

## Running the Server

You can run the MCP server using Uvicorn:

```bash
uvicorn main:mcp --host 0.0.0.0 --port 8000 --reload
```

*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on (adjust if needed).
*   `--reload`: Automatically restarts the server when code changes (useful for development).

Alternatively, if `FastMCP` provides a built-in run command, you might be able to run it directly:

```bash
python main.py
```

Check the console output for the address where the server is running (e.g., `http://127.0.0.1:8000`).

## Available Tools

This MCP server provides the following tool:

### `chat_completion`

*   **Description:** Performs a deep search and reasoning process based on a conversation history. It takes user queries, searches the web, reads relevant content, and iteratively reasons to find the best answer. Supports streaming responses, domain filtering, and control over reasoning effort.
*   **Input:** `DeepSearchChatInput` model
    *   `messages` (List[ChatMessage], required): Conversation history (user/assistant roles, text/image/document content).
    *   `model` (str, optional, default: "jina-deepsearch-v1"): ID of the DeepSearch model.
    *   `stream` (bool, optional, default: True): Enable streaming response (recommended).
    *   `reasoning_effort` (Literal['low', 'medium', 'high'], optional, default: 'medium'): Control reasoning depth.
    *   `budget_tokens` (int, optional): Max token budget.
    *   `max_attempts` (int, optional): Max retry attempts.
    *   `no_direct_answer` (bool, optional, default: False): Force search/thinking steps.
    *   `max_returned_urls` (int, optional): Max URLs in the final answer.
    *   `structured_output` (Dict[str, Any], optional): JSON schema for structured output.
    *   `good_domains` (List[str], optional): Prioritized domains.
    *   `bad_domains` (List[str], optional): Excluded domains.
    *   `only_domains` (List[str], optional): Exclusively included domains.
*   **Output:**
    *   If `stream=False`: A single `DeepSearchChatResponse` object.
    *   If `stream=True`: An `AsyncGenerator` yielding `DeepSearchChatChunk` objects.

## Example Usage (Conceptual)

Using an MCP client (like `mcp-client` CLI or a Python library):

**Non-Streaming:**

```python
from mcp import MCPClient

client = MCPClient(host='localhost', port=8000)

input_data = {
    "messages": [
        {"role": "user", "content": "Explain the concept of quantum entanglement in simple terms."}
    ],
    "stream": False,
    "reasoning_effort": "medium"
}

response = await client.call('deepsearch', 'chat_completion', input_data=input_data)

print(response)
# Output: DeepSearchChatResponse object
```

**Streaming:**

```python
from mcp import MCPClient

client = MCPClient(host='localhost', port=8000)

input_data = {
    "messages": [
        {"role": "user", "content": "Explain the concept of quantum entanglement in simple terms."}
    ],
    "stream": True
}

async for chunk in await client.stream('deepsearch', 'chat_completion', input_data=input_data):
    print(chunk)
    # Output: DeepSearchChatChunk objects as they arrive
```

## Error Handling

The server includes error handling for common issues:

*   **Authentication Errors:** If the `JINA_API_KEY` is missing or invalid.
*   **Invalid Requests:** If the input data format is incorrect.
*   **Rate Limits:** If the API rate limits are exceeded.
*   **Server Errors:** If the DeepSearch API encounters internal errors.
*   **Network/Timeout Errors:** If the connection to the API fails or times out.

Errors from the DeepSearch API will be propagated as exceptions, which FastMCP should translate into appropriate MCP error responses.
