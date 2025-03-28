# Jina AI DeepSearch MCP Server

This repository provides a Model Context Protocol (MCP) server for interacting with the [Jina AI DeepSearch API](https://jina.ai/deepsearch/).

DeepSearch combines web searching, reading, and reasoning to provide comprehensive answers to complex questions. It functions as an autonomous agent that iteratively searches, reads, and reasons, dynamically deciding the next steps based on its findings.

This MCP server exposes the core functionality of DeepSearch through a standardized tool interface.

## Features

*   **`chat_completion` Tool:** Performs a deep search and reasoning process based on a conversation history. It mimics the interface of OpenAI's Chat Completion API but leverages DeepSearch's advanced web search and analysis capabilities.
    *   Supports text, image, and file inputs within messages.
    *   Handles streaming responses (recommended) and aggregates them into a final result.
    *   Allows configuration of reasoning effort, token budget, domain preferences, and more.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create a `.env` file:**
    Copy the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env`:**
    Replace `your_jina_api_key_here` with your actual Jina AI API key. You can obtain a key from the [Jina AI Cloud Platform](https://cloud.jina.ai/).
    ```dotenv
    JINA_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    ```
    *   You can optionally override the `DEEPSEARCH_BASE_URL` if needed, but the default (`https://deepsearch.jina.ai/v1`) is usually correct.

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will start, typically on `http://127.0.0.1:8000` (or the configured MCP host/port).

## Usage

You can interact with the server using an MCP client, such as the `mcp` CLI.

**Example using `mcp` CLI:**

```bash
# List available tools
# mcp list --url http://127.0.0.1:8000

# Call the chat_completion tool
mcp call --url http://127.0.0.1:8000 deepsearch.chat_completion \\
    --param 'params={ "model": "jina-deepsearch-v1", "messages": [{"role": "user", "content": "What were the key advancements in AI in 2023?"}] }'

# Example with more options (ensure proper JSON escaping in your shell)
mcp call --url http://127.0.0.1:8000 deepsearch.chat_completion \\
    --param 'params={ "model": "jina-deepsearch-v1", "messages": [{"role": "user", "content": "Compare the performance of Llama 2 and GPT-4 on coding tasks, citing sources."}], "reasoning_effort": "high", "max_returned_urls": 5 }'
```

**Note:** When using complex JSON structures like `messages` or `structured_output` via the CLI, ensure correct JSON formatting and shell escaping.

## Error Handling

The server includes error handling for:

*   API authentication issues (invalid/missing API key).
*   API rate limits.
*   Invalid input parameters.
*   Timeouts (especially if streaming is disabled).
*   Server-side errors from the DeepSearch API.
*   Network issues.

Errors from the API or the MCP tool itself will be returned in a JSON response containing an `"error"` key.
