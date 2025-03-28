# DeepSearch MCP Server

This project provides a Model Context Protocol (MCP) server for Jina AI's DeepSearch API, implemented using FastMCP.

DeepSearch offers advanced search, reading, and reasoning capabilities to answer complex questions by iteratively searching the web. This MCP server exposes the DeepSearch functionality through an OpenAI-compatible Chat Completions API schema.

## Features

*   Provides the `chat_completion` tool mirroring the DeepSearch `/v1/chat/completions` endpoint.
*   Supports all DeepSearch parameters (streaming, reasoning effort, domain filtering, structured output, etc.).
*   Handles authentication using Jina API keys.
*   Includes robust error handling for API errors, timeouts, rate limits, and connection issues.
*   Supports streaming responses using Server-Sent Events (SSE).
*   Built with FastMCP for easy integration into MCP ecosystems.

## Prerequisites

*   Python 3.8+
*   A Jina AI API Key (get one from [Jina AI Cloud](https://jina.ai/cloud/))

## Setup

1.  **Clone the repository (or create the files):**
    ```bash
    # If you have the code in a directory
    cd /path/to/your/deepsearch-mcp
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
    Create a `.env` file in the project root directory by copying the example:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Jina API key:
    ```env
    JINA_API_KEY="YOUR_JINA_API_KEY_HERE"
    # DEEPSEARCH_BASE_URL="https://deepsearch.jina.ai" # Optional: uncomment to override default
    ```

## Running the Server

You can run the server directly using Python for development:

```bash
python main.py
```

For production deployments, it's recommended to use an ASGI server like Uvicorn:

```bash
# Make sure uvicorn is installed: pip install uvicorn
uvicorn main:mcp.app --host 0.0.0.0 --port 8000 --reload # --reload is for development
```

The server will be available at `http://localhost:8000` (or the host/port you specify).

## Available Tools

This MCP server exposes one primary tool:

### `chat_completion`

*   **Description:** Performs iterative search, reading, and reasoning using the DeepSearch model to answer user queries. Takes a conversation history and various parameters to control the search and reasoning process. Returns a detailed response including the answer, citations, and usage statistics.
*   **Input Model:** `DeepSearchChatInput` (see `models.py` for details)
    *   `messages` (List[Message]): Conversation history (required).
    *   `model` (str): DeepSearch model ID (required).
    *   `stream` (Optional[bool]): Enable streaming (default: True).
    *   `reasoning_effort` (Optional[str]): 'low', 'medium', 'high' (default: 'medium').
    *   `budget_tokens` (Optional[int]): Max token budget.
    *   `max_attempts` (Optional[int]): Max retry attempts.
    *   `no_direct_answer` (Optional[bool]): Force search steps (default: False).
    *   `max_returned_urls` (Optional[int]): Max URLs in the final answer.
    *   `structured_output` (Optional[Dict]): JSON schema for output structure.
    *   `good_domains` (Optional[List[str]]): Prioritized domains.
    *   `bad_domains` (Optional[List[str]]): Excluded domains.
    *   `only_domains` (Optional[List[str]]): Exclusively included domains.
*   **Returns:** `DeepSearchChatOutput` (Dictionary or AsyncGenerator[Dict]) - OpenAI-compatible chat completion response, potentially including `visited_urls` and `read_urls`.

## Example Usage (using `curl`)

**Non-Streaming:**

```bash
curl -X POST http://localhost:8000/tools/chat_completion \\
-H "Content-Type: application/json" \\
-d '{
  "params": {
    "model": "jina-deepsearch-v1",
    "messages": [
      {"role": "user", "content": "What are the main benefits of using Jina AI?"}
    ],
    "stream": false
  }
}'
```

**Streaming:**

```bash
curl -X POST http://localhost:8000/tools/chat_completion \\
-H "Content-Type: application/json" \\
-H "Accept: text/event-stream" \\
-d '{
  "params": {
    "model": "jina-deepsearch-v1",
    "messages": [
      {"role": "user", "content": "Explain the concept of Retrieval-Augmented Generation (RAG)."}
    ],
    "stream": true
  }
}'
```

(Note: The streaming request will return Server-Sent Events.)

## Error Handling

The server maps errors from the DeepSearch API and the client itself to structured JSON error responses, often mimicking the OpenAI error schema where applicable:

*   `AuthenticationError` (401/403)
*   `RateLimitError` (429)
*   `BadRequestError` (400)
*   `TimeoutError` (504)
*   `APIError` (5xx)
*   `ConnectionError` (503)
*   Other `DeepSearchError` or unexpected errors (500)

## Project Structure

```
.
├── .env.example        # Example environment variables
├── .env                # Actual environment variables (ignored by git)
├── client.py           # DeepSearch API client implementation
├── main.py             # FastMCP server application
├── models.py           # Pydantic models for API requests/responses
├── README.md           # This documentation file
└── requirements.txt    # Python dependencies
```
