# Jina DeepSearch MCP Server

This repository contains an MCP (Model Context Protocol) server implementation for interacting with the [Jina AI DeepSearch API](https://jina.ai/deepsearch/) using [FastMCP](https://github.com/cognosis-ai/mcp?).

DeepSearch combines web searching, reading, and reasoning to provide comprehensive answers to complex questions, especially those requiring up-to-date information or iterative investigation. It is designed to be compatible with the OpenAI Chat API schema.

## Features

*   Provides an MCP interface to the Jina DeepSearch `/v1/chat/completions` endpoint.
*   Handles authentication using a Jina API key.
*   Supports streaming responses (recommended and default) with internal aggregation.
*   Includes Pydantic models for request validation and response parsing.
*   Basic error handling for API errors, timeouts, and request issues.

## Setup

1.  **Clone the repository (or create the files):**
    ```bash
    # If cloned:
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory by copying the example:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Jina AI API key:
    ```env
    JINA_API_KEY="your_jina_api_key_here"
    ```
    You can obtain an API key from the [Jina AI Cloud dashboard](https://jina.ai/cloud/).

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will typically start on `http://localhost:8000` (or the default FastMCP port).

## Available Tools

### `chat_completion`

Sends a chat conversation to the DeepSearch model (`jina-deepsearch-v1`) for processing.

**Description:** The model performs iterative search, reading, and reasoning to generate a comprehensive answer, citing sources. Supports text, images (webp, png, jpeg encoded as data URIs), and documents (txt, pdf encoded as data URIs) within messages. Streaming is recommended and handled by default; this tool returns the aggregated final response.

**Input Parameters (`DeepSearchChatInput` model):**

*   `messages` (List[`ChatMessage`], **required**): A list of messages comprising the conversation history. See `ChatMessage` structure below.
*   `model` (str, optional, default: `"jina-deepsearch-v1"`): ID of the model to use.
*   `stream` (bool, optional, default: `True`): Whether to stream the response. Strongly recommended. The tool aggregates the stream.
*   `reasoning_effort` (str, optional, default: `"medium"`): Constrains reasoning effort (`'low'`, `'medium'`, `'high'`).
*   `budget_tokens` (int, optional): Maximum tokens allowed for the DeepSearch process.
*   `max_attempts` (int, optional): Maximum number of retries for solving the problem.
*   `no_direct_answer` (bool, optional, default: `False`): Forces thinking/search steps.
*   `max_returned_urls` (int, optional): Maximum number of URLs in the final answer.
*   `structured_output` (Dict[str, Any], optional): A JSON schema for structured output.
*   `good_domains` (List[str], optional): List of domains to prioritize.
*   `bad_domains` (List[str], optional): List of domains to exclude.
*   `only_domains` (List[str], optional): List of domains to exclusively include.

**`ChatMessage` Structure:**

```python
{
  "role": "user" | "assistant" | "system",
  "content": "text content" | [
    {"type": "text", "text": "..."},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
    {"type": "document_url", "document_url": {"url": "data:application/pdf;base64,..."}}
  ],
  "name": Optional[str]
}
```

**Returns (`DeepSearchChatResponse` model):**

A dictionary containing the aggregated response from the API, including:

*   `id` (str): Unique ID for the completion.
*   `object` (str): Object type (`chat.completion`).
*   `created` (int): Timestamp.
*   `model` (str): Model used.
*   `choices` (List[`ResponseChoice`]): List containing the generated message and finish reason.
*   `usage` (Optional[`UsageStats`]): Token usage information.
*   `visitedURLs` (Optional[List[str]]): URLs visited during search.
*   `readURLs` (Optional[List[str]]): URLs read for the answer.
*   `numURLs` (Optional[int]): Total unique URLs encountered.
*   `error` (str, optional): Present if an error occurred during processing.

## Authentication

The server uses Bearer Token authentication. The `JINA_API_KEY` from your `.env` file is automatically included in the `Authorization` header for requests made to the Jina DeepSearch API.

## Error Handling

The server attempts to catch and log common errors:

*   **API Errors:** Catches `HTTPStatusError` from `httpx` and wraps them in `DeepSearchAPIError`, returning a JSON error message with the status code and message from the API response if available.
*   **Timeouts:** Catches `httpx.TimeoutException`.
*   **Request Errors:** Catches other `httpx.RequestError` issues (e.g., connection problems).
*   **Unexpected Errors:** Catches general exceptions during tool execution.

## Rate Limits

The Jina DeepSearch API has rate limits (e.g., 10 RPM for standard keys). If you exceed the rate limit, the API will return a `429 Too Many Requests` error, which will be caught and reported by the MCP tool. Implementations consuming this MCP should handle potential rate limit errors gracefully (e.g., with backoff and retry logic).
