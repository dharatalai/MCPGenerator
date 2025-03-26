## API Endpoints

### POST /deepsearch_chat_completions

Execute a DeepSearch query with streaming response.

**Parameters:**
- `model` (str): ID of the model to use (default: "jina-deepsearch-v1")
- `messages` (List[Message]): Conversation history
- `stream` (bool): Enable streaming (default: True)
- `reasoning_effort` (str): Level of reasoning (low/medium/high, default: medium)
- `budget_tokens` (int, optional): Token budget
- `max_attempts` (int, optional): Maximum retries
- `no_direct_answer` (bool): Force thinking steps (default: False)
- `max_returned_urls` (int, optional): Max URLs in response
- `structured_output` (bool): Enable structured output (default: False)
- `good_domains` (List[str], optional): Preferred domains
- `bad_domains` (List[str], optional): Excluded domains
- `only_domains` (List[str], optional): Only these domains

**Response:**
Stream of `ResponseChunk` objects with content and type fields.

## Error Handling

The server handles:
- HTTP errors (returns appropriate status codes)
- Timeouts (408 status code)
- Rate limiting (429 status code)
- Validation errors (400 status code)

## Rate Limits

The server enforces a rate limit of 10 requests per minute to match the DeepSearch API limits.