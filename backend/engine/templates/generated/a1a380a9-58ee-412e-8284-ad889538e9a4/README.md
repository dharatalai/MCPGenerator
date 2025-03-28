# Jina AI DeepSearch MCP Server

This repository contains an MCP (Model Context Protocol) server implementation for interacting with the Jina AI DeepSearch API.

## Description

The `jina_deepsearch` MCP service provides access to Jina AI's DeepSearch capabilities. DeepSearch is designed to answer complex questions by iteratively searching the web, reading relevant content, and reasoning to synthesize an accurate answer. It supports multimodal inputs (text, images, documents) and provides citations for its generated answers.

This server uses the `FastMCP` framework and interacts with the Jina AI DeepSearch API endpoint (`https://deepsearch.jina.ai/v1/chat/completions`), which is compatible with the OpenAI Chat Completions API schema.

## Features

*   Provides a single tool: `chat_completion`.
*   Handles authentication using Jina AI API keys (Bearer Token).
*   Supports streaming responses (recommended) and aggregates them into a final result.
*   Includes Pydantic models for robust input validation and output parsing.
*   Implements error handling for common API issues (authentication, rate limits, invalid requests, server errors).
*   Configurable via environment variables.

## Tools

### 1. `chat_completion`

*   **Description**: Performs a deep search and reasoning process based on a conversation history. It iteratively searches the web, reads content, and reasons to find the best answer to the user's query. Supports text, image (webp, png, jpeg as data URI), and document (txt, pdf as data URI) inputs in messages. Returns the final aggregated answer along with metadata.
*   **Input**: `DeepSearchChatInput` model
    *   `messages` (List[Message], **required**): Conversation history. Last message must be from 'user'.
        *   `Message`: `{ "role": "user" | "assistant", "content": "text or data URI" }`
    *   `model` (str, optional, default: `"jina-deepsearch-v1"`): Model ID.
    *   `stream` (bool, optional, default: `True`): *Note: The server internally forces streaming for aggregation, but you can include this parameter.* 
    *   `reasoning_effort` (str, optional, default: `"medium"`): Constraint on reasoning ('low', 'medium', 'high').
    *   `budget_tokens` (int, optional): Max tokens for the process.
    *   `max_attempts` (int, optional): Max retries for solving.
    *   `no_direct_answer` (bool, optional, default: `False`): Force search/thinking steps.
    *   `max_returned_urls` (int, optional): Max URLs in the final answer.
    *   `structured_output` (dict, optional): JSON schema for the output structure.
    *   `good_domains` (List[str], optional): Prioritized domains.
    *   `bad_domains` (List[str], optional): Excluded domains.
    *   `only_domains` (List[str], optional): Exclusively included domains.
*   **Output**: `DeepSearchChatResponse` model (dictionary representation)
    *   `id` (str): Unique completion ID.
    *   `object` (str): `"chat.completion"`.
    *   `created` (int): Timestamp.
    *   `model` (str): Model used.
    *   `choices` (List[Choice]): List containing the response.
        *   `Choice`: `{ "index": int, "message": ResponseMessage, "finish_details": FinishDetails }`
        *   `ResponseMessage`: `{ "role": "assistant", "content": str }`
        *   `FinishDetails`: `{ "type": str, "stop": Optional[str], "url_citations": Optional[List[UrlCitation]] }`
        *   `UrlCitation`: `{ "title": Optional[str], "exactQuote": Optional[str], "url": str, "dateTime": Optional[str] }`
    *   `usage` (Optional[Usage]): Token usage statistics.
        *   `Usage`: `{ "prompt_tokens": int, "completion_tokens": Optional[int], "total_tokens": int }`

## Setup

1.  **Clone the repository (or save the generated files):**
    ```bash
    # If you have a git repo
    # git clone <repository_url>
    # cd <repository_directory>
    
    # Or just save main.py, api.py, models.py, requirements.txt, .env.example
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
        JINA_API_KEY=your_jina_api_key_here
        ```
    *   You can obtain an API key from [Jina AI](https://jina.ai/).

## Running the Server

Start the MCP server using the `main.py` script:

```bash
python main.py
```

The server will typically start on `http://127.0.0.1:8000` (or the default FastMCP port).

## Usage Example (Conceptual MCP Client)

```python
from mcp import MCPClient

async def main():
    client = MCPClient("http://127.0.0.1:8000") # URL of your running MCP server

    try:
        response = await client.tools.jina_deepsearch.chat_completion(
            messages=[
                {"role": "user", "content": "What were the key advancements in AI in 2023?"}
            ],
            reasoning_effort="high"
        )
        
        if "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("DeepSearch Response:")
            print(f"ID: {response.get('id')}")
            if response.get('choices'):
                print(f"Answer: {response['choices'][0]['message']['content']}")
                citations = response['choices'][0].get('finish_details', {}).get('url_citations')
                if citations:
                    print("\
Citations:")
                    for cit in citations:
                        print(f"- [{cit.get('title', 'N/A')}]({cit['url']})")
            if response.get('usage'):
                 print(f"\
Usage: {response['usage']}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Error Handling

The server attempts to catch common errors from the Jina API and returns them in a structured JSON format: `{"error": "Error message"}`.

*   **AuthenticationError**: Invalid or missing API key (HTTP 401).
*   **RateLimitError**: API rate limit exceeded (HTTP 429).
*   **InvalidRequestError**: Malformed request payload (HTTP 400).
*   **ServerError**: Jina API server-side error (HTTP 5xx).
*   **TimeoutError**: Request to Jina API timed out.
*   **DeepSearchError**: Other API-specific or stream processing errors.
