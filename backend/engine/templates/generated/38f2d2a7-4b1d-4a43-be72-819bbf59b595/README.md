# Deepsearch MCP Server

This project provides a Model Context Protocol (MCP) server built with FastMCP to interact with a hypothetical "Deepsearch" API. Deepsearch is assumed to be a service that takes a query and returns a generated answer based on relevant search results (similar to RAG - Retrieval-Augmented Generation).

## Features

*   Provides MCP tools to perform searches via the Deepsearch API.
*   Uses Pydantic for request and response validation.
*   Includes asynchronous API client (`httpx`).
*   Handles API authentication via environment variables.
*   Includes error handling and logging.
*   Configurable via environment variables.

## Prerequisites

*   Python 3.8+
*   Access to a Deepsearch API (or equivalent) and its API key/base URL.

## Setup

1.  **Clone the repository (or download the files):**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
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
    *   Edit the `.env` file and add your actual Deepsearch API key and base URL:
        ```dotenv
        DEEPSEARCH_API_KEY="your_actual_api_key"
        DEEPSEARCH_API_BASE_URL="https://actual.api.base.url"
        ```

## Running the Server

Start the MCP server using Uvicorn (which is installed as part of `uvicorn[standard]`):

```bash
python main.py
```

Or directly with uvicorn for more options (like hot-reloading):

```bash
# Ensure venv is active
uvicorn main:mcp --reload --host 127.0.0.1 --port 8000
```

The server will be available at `http://127.0.0.1:8000` by default.

## Available MCP Tools

The server exposes the following tools:

1.  **`deep_search`**
    *   **Description:** Performs a search using the Deepsearch API with default settings.
    *   **Input:**
        *   `query` (string, required): The search query.
    *   **Output:** `DeepsearchResult` (object containing `answer`, `sources`, `usage`) or `ErrorResponse`.

2.  **`deep_search_custom`**
    *   **Description:** Performs a search using the Deepsearch API with custom parameters.
    *   **Input:** `params` (object)
        *   `query` (string, required): The search query.
        *   `model` (string, optional, default: "deepsearch-default"): The model to use.
        *   `max_results` (integer, optional, default: 10): Max results to use/return.
    *   **Output:** `DeepsearchResult` (object containing `answer`, `sources`, `usage`) or `ErrorResponse`.

## API Client (`DeepsearchAPIClient`)

The `main.py` includes a `DeepsearchAPIClient` class responsible for:

*   Reading API key and base URL from environment variables.
*   Constructing API request headers (including Authorization).
*   Making asynchronous POST requests to the `/v1/search` endpoint (configurable).
*   Handling HTTP errors (4xx, 5xx), timeouts, and connection errors.
*   Parsing the JSON response.

**Note:** The specific API endpoint (`/v1/search`) and the request/response structure are based on assumptions. You may need to modify `DeepsearchAPIClient.search` and the Pydantic models (`DeepsearchQueryParams`, `DeepsearchResult`, `Source`, `DeepsearchUsage`) to match the actual Deepsearch API specification.

## Error Handling

*   The API client raises specific exceptions (`TimeoutError`, `ConnectionError`) for network/API issues.
*   MCP tools catch these exceptions and return a structured `ErrorResponse` object.
*   Unexpected errors within the tools also return an `ErrorResponse`.
*   Failures during API client initialization (missing environment variables) are logged critically.

## Authentication

*   **API Authentication:** The server authenticates with the Deepsearch API using a Bearer token (API key) provided via the `DEEPSEARCH_API_KEY` environment variable.
*   **MCP Server Authentication:** This implementation does *not* include authentication for accessing the MCP server itself. If required, this should be handled at a higher level, for example, using a reverse proxy (like Nginx or Traefik) or by leveraging MCP's built-in authentication features if available/configured.
