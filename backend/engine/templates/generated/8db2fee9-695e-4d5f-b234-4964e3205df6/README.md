# DeepSearch MCP Server

This repository contains an MCP (Model Context Protocol) server implementation for the Jina AI DeepSearch API, built using FastMCP.

## Overview

The Jina AI DeepSearch API provides advanced search capabilities by combining web searching, content reading, and iterative reasoning. It's designed to answer complex questions requiring real-time information, multi-hop reasoning, or in-depth research. The API follows the OpenAI Chat API schema.

This MCP server exposes the DeepSearch functionality as a standard MCP tool, allowing easy integration into multi-agent systems or other applications using MCP.

## Features

*   **DeepSearch Integration:** Connects to the Jina AI DeepSearch API.
*   **OpenAI Schema Compatibility:** Uses Pydantic models matching the OpenAI chat completion schema for input and output.
*   **Multimodal Support:** Accepts text, images (via data URI or URL), and documents (via data URI) as input within the message history.
*   **Structured Output:** Returns the answer, cited sources, and token usage information.
*   **Error Handling:** Includes robust error handling for API errors, network issues, and timeouts.
*   **Authentication:** Uses API key authentication (via `JINA_API_KEY` environment variable).
*   **Configuration:** Configurable via environment variables.

## Tools

### `chat_completion`

*   **Description:** Initiates a DeepSearch process based on a conversation history. The API iteratively searches the web, reads relevant content, and performs reasoning steps to arrive at the most accurate answer possible. The final response includes the answer, cited sources (URLs), and token usage statistics.
*   **Input:** `DeepSearchChatInput` model (see `models.py`)
    *   `messages`: A list of `Message` objects representing the conversation history. Each message has a `role` (`user`, `assistant`, `system`) and `content`. `content` can be a string or a list for multimodal input (text, images, documents).
    *   `stream`: (Optional) Boolean, defaults to `false`. While the API supports streaming, this server currently returns the final aggregated response.
*   **Output:** `DeepSearchChatOutput` model (see `models.py`)
    *   `answer`: The final generated answer.
    *   `sources`: A list of cited sources (`url`, `title`, `snippet`).
    *   `usage`: Token usage statistics (`prompt_tokens`, `completion_tokens`, `total_tokens`).
    *   Other standard OpenAI response fields (`id`, `object`, `created`, `model`, etc.).

## Setup and Installation

1.  **Clone the repository (or create the files):**
    ```bash
    # If cloning a repo:
    # git clone <repository_url>
    # cd <repository_directory>

    # If creating files manually, ensure you have:
    # main.py, api.py, models.py, requirements.txt, .env.example, README.md
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
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and add your Jina AI API key:
        ```env
        JINA_API_KEY="your_jina_api_key_here"
        ```
    *   You can obtain a Jina AI API key from [Jina AI Cloud](https://cloud.jina.ai/).
    *   Optionally, set `MCP_HOST` and `MCP_PORT` in the `.env` file if you want to run the server on a different address or port (defaults usually to `0.0.0.0:8000`).

## Running the Server

Start the MCP server using:

```bash
python main.py
```

The server will start, typically on `http://0.0.0.0:8000` (or as configured).

## Usage Example (using `mcp-client`)

```python
import asyncio
from mcp.client.aio import MCPClient

async def main():
    client = MCPClient("http://localhost:8000") # Adjust URL if needed

    messages = [
        {
            "role": "user",
            "content": "What were the key announcements from the latest Apple event?"
        }
    ]

    try:
        response = await client.run_tool(
            tool_name="chat_completion",
            params={"messages": messages}
        )
        
        if "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("Answer:", response.get("answer"))
            print("\
Sources:")
            for source in response.get("sources", []):
                print(f"- {source.get('title', 'N/A')}: {source.get('url')}")
            print("\
Usage:", response.get("usage"))
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Development Notes

*   **Streaming:** The DeepSearch API supports streaming responses. While the `stream` parameter is included in the input model, the current `api.py` client implementation waits for and processes the final aggregated response. To fully support streaming, the `api_client.chat_completion` method and the MCP tool would need to be adapted to handle Server-Sent Events (SSE) and potentially yield intermediate results.
*   **Error Handling:** The server includes basic error handling, but specific API error codes from Jina might require more tailored handling based on their documentation.
*   **Model Customization:** The client currently defaults to the `jina-deepsearch` model. This could be made configurable if needed.
