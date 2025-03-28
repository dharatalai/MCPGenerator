# Jina DeepSearch MCP Server

This repository contains a Model Context Protocol (MCP) server for interacting with the [Jina DeepSearch API](https://jina.ai/deepsearch/).

DeepSearch combines web searching, reading, and reasoning to act as an agent performing iterative research. It aims to find the best answer to complex questions requiring world-knowledge or up-to-date information. The API is designed to be compatible with OpenAI's Chat API schema.

This server is built using [FastMCP](https://github.com/datascienceai/fastmcp). 

## Features

*   Provides an MCP interface to Jina DeepSearch's `chat/completions` endpoint.
*   Supports both streaming and non-streaming responses.
*   Handles multimodal inputs (text, images via data URI, documents via data URI).
*   Configurable reasoning effort, token budget, domain filtering, and more.
*   Proper error handling and logging.
*   Authentication via Jina API Key.

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
    Edit the `.env` file and add your Jina API Key:
    ```ini
    JINA_API_KEY=your_jina_api_key_here
    ```
    You can obtain a Jina API key from the [Jina AI Cloud](https://jina.ai/cloud/).

## Running the Server

Start the MCP server using:

```bash
python main.py
```

By default, the server will run on `http://127.0.0.1:8000`. You can configure the host and port using environment variables (`HOST`, `PORT`) or by modifying the `mcp.run()` call in `main.py`.

## Available Tools

### `chat_completions`

Initiates a DeepSearch process based on a conversation history.

**Description:** Performs iterative search, reading, and reasoning. Supports streaming responses (recommended) to receive intermediate thinking steps and the final answer.

**Input Model:** `DeepSearchChatInput`

*   `messages` (List[Message], **required**): Conversation history. Can include text, images (webp, png, jpeg via data URI), or documents (txt, pdf via data URI up to 10MB).
*   `model` (str, optional, default: "jina-deepsearch-v1"): ID of the model to use.
*   `stream` (bool, optional, default: `True`): Whether to stream responses. **Strongly recommended** to avoid timeouts.
*   `reasoning_effort` (str, optional, default: "medium"): Constrains reasoning ('low', 'medium', 'high').
*   `budget_tokens` (int, optional): Maximum tokens allowed for the process.
*   `max_attempts` (int, optional): Maximum retries with different approaches.
*   `no_direct_answer` (bool, optional, default: `False`): Forces further thinking/search steps.
*   `max_returned_urls` (int, optional): Maximum URLs in the final answer.
*   `structured_output` (Dict, optional): JSON schema for the final answer structure.
*   `good_domains` (List[str], optional): Domains to prioritize.
*   `bad_domains` (List[str], optional): Domains to exclude.
*   `only_domains` (List[str], optional): Domains to exclusively include.

**Returns:**

*   If `stream=False`: A dictionary representing the `ChatCompletion` object containing the final answer, usage stats, and visited URLs.
*   If `stream=True`: An asynchronous generator yielding dictionaries representing `ChatCompletionChunk` objects. The last chunk contains final details and usage stats.
*   On error: A dictionary containing an `error` message and `status_code`.

## Authentication

The server uses Bearer Token authentication. The Jina API Key provided in the `.env` file (`JINA_API_KEY`) is automatically included in the `Authorization` header for requests to the Jina DeepSearch API.

## Error Handling

The server handles:

*   HTTP errors (4xx, 5xx) from the Jina API.
*   Network connection errors.
*   Request/response validation errors.
*   Timeouts (handled by `httpx` client timeout setting).

Errors are logged, and an error dictionary is returned by the tool in case of failure.

## Rate Limits

The Jina DeepSearch API has rate limits (e.g., 10 requests per minute as per the plan). This MCP server itself does not implement additional rate limiting beyond what the API enforces. Ensure your usage complies with Jina's terms of service.
