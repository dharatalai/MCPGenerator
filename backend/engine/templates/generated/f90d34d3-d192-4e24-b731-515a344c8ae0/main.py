from mcp.server.fastmcp import FastMCP, ToolContext
from typing import Dict, Any, List, Optional
import logging
import asyncio
import os
import json
from dotenv import load_dotenv
import httpx

from models import (
    DeepSearchChatParams,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ResponseMessage,
    Choice,
    Usage,
    Annotation
)
from api import JinaDeepSearchAPIClient

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP(
    service_name="jina_deepsearch",
    description="Provides access to Jina DeepSearch, an AI agent that combines web searching, reading, and reasoning to answer complex questions requiring iterative investigation and up-to-date information. It is compatible with the OpenAI Chat API schema."
)

# Initialize API Client
try:
    api_client = JinaDeepSearchAPIClient()
except ValueError as e:
    logger.error(f"Failed to initialize API client: {e}")
    # Allow MCP server to start, but tools will fail
    api_client = None

async def parse_sse_chunk(line: str) -> Optional[ChatCompletionChunk]:
    """Parses a single line from an SSE stream into a ChatCompletionChunk."""
    if line.startswith('data: '):
        data_str = line[len('data: '):].strip()
        if data_str == "[DONE]":
            return None
        try:
            data_json = json.loads(data_str)
            return ChatCompletionChunk.model_validate(data_json)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON from SSE line: {data_str}")
        except Exception as e:
            logger.warning(f"Failed to validate SSE chunk: {e}, data: {data_str}")
    return None

async def aggregate_stream(stream: AsyncGenerator[bytes, None]) -> ChatCompletionResponse:
    """Aggregates SSE chunks from the stream into a final ChatCompletionResponse."""
    final_response_data = {
        "id": None,
        "object": "chat.completion",
        "created": None,
        "model": None,
        "choices": [],
        "usage": {},
        "visited_urls": [],
        "read_urls": []
    }
    accumulated_choices = {}
    current_line = b''

    async for chunk_bytes in stream:
        current_line += chunk_bytes
        # Process lines separated by \
\
, \\r\
\\r\
, or \\r\\r
        while b'\
\
' in current_line or b'\\r\
\\r\
' in current_line or b'\\r\\r' in current_line:
            if b'\
\
' in current_line:
                line_bytes, current_line = current_line.split(b'\
\
', 1)
            elif b'\\r\
\\r\
' in current_line:
                line_bytes, current_line = current_line.split(b'\\r\
\\r\
', 1)
            else: # \\r\\r
                line_bytes, current_line = current_line.split(b'\\r\\r', 1)

            line = line_bytes.decode('utf-8').strip()
            if not line:
                continue

            # SSE format can have multiple lines per event, split by \
 or \\r
            for single_line in line.replace('\\r\
', '\
').replace('\\r', '\
').split('\
'):
                chunk = await parse_sse_chunk(single_line.strip())
                if chunk:
                    # Capture top-level fields from the first chunk
                    if final_response_data["id"] is None: final_response_data["id"] = chunk.id
                    if final_response_data["created"] is None: final_response_data["created"] = chunk.created
                    if final_response_data["model"] is None: final_response_data["model"] = chunk.model

                    # Aggregate choices
                    for choice_chunk in chunk.choices:
                        idx = choice_chunk.index
                        if idx not in accumulated_choices:
                            accumulated_choices[idx] = {
                                "index": idx,
                                "message": {"role": None, "content": "", "annotations": []},
                                "finish_reason": None
                            }

                        delta = choice_chunk.delta
                        if delta.role is not None:
                            accumulated_choices[idx]["message"]["role"] = delta.role
                        if delta.content is not None:
                            accumulated_choices[idx]["message"]["content"] += delta.content
                        if delta.annotations is not None:
                            # Assuming annotations list replaces previous ones or appends?
                            # OpenAI typically appends content, but other fields might replace.
                            # Let's assume replacement for simplicity unless API docs specify otherwise.
                            # If they are additive, logic needs adjustment.
                            # Jina's example suggests annotations might come at the end or replace.
                            # Let's try merging/appending carefully.
                            if accumulated_choices[idx]["message"]["annotations"] is None:
                                accumulated_choices[idx]["message"]["annotations"] = []
                            # Simple append might duplicate if sent multiple times. Need smarter merge.
                            # For now, let's just take the last non-null list.
                            accumulated_choices[idx]["message"]["annotations"] = delta.annotations

                        if choice_chunk.finish_reason is not None:
                            accumulated_choices[idx]["finish_reason"] = choice_chunk.finish_reason

                    # Capture usage, visited_urls, read_urls (often in the last chunk)
                    if chunk.usage:
                        final_response_data["usage"] = chunk.usage.model_dump(exclude_none=True)
                    if chunk.visited_urls:
                        final_response_data["visited_urls"] = chunk.visited_urls
                    if chunk.read_urls:
                        final_response_data["read_urls"] = chunk.read_urls

    # Assemble final response
    final_choices = []
    for idx in sorted(accumulated_choices.keys()):
        choice_data = accumulated_choices[idx]
        # Ensure annotations list is initialized if it remained None
        if choice_data["message"]["annotations"] is None:
            choice_data["message"]["annotations"] = []
        final_choices.append(
            Choice(
                index=choice_data["index"],
                message=ResponseMessage.model_validate(choice_data["message"]),
                finish_reason=choice_data["finish_reason"]
            )
        )

    final_response_data["choices"] = final_choices
    final_response_data["usage"] = Usage.model_validate(final_response_data["usage"])

    # Validate the final aggregated structure
    try:
        return ChatCompletionResponse.model_validate(final_response_data)
    except Exception as e:
        logger.error(f"Failed to validate final aggregated response: {e}\
Data: {final_response_data}")
        raise ValueError(f"Failed to construct final response: {e}")

@mcp.tool()
async def chat_completion(params: DeepSearchChatParams, context: ToolContext) -> Dict[str, Any]:
    """
    Performs a deep search and reasoning process based on a conversation history
    to generate a comprehensive answer. Suitable for complex questions requiring
    iterative research, world-knowledge, or up-to-date information.
    Handles streaming internally and returns the final aggregated response.

    Args:
        params: Parameters for the chat completion request, including messages,
                model, and other options.
        context: The MCP ToolContext.

    Returns:
        A dictionary representing the final aggregated ChatCompletionResponse.
    """
    if not api_client:
        logger.error("API client not initialized. Cannot call chat_completion.")
        return {"error": "API client not initialized. Check JINA_API_KEY."}

    logger.info(f"Received chat_completion request for model {params.model}")
    # Ensure stream=True is used for the API call, as aggregation is handled here.
    params.stream = True

    try:
        stream = api_client.chat_completion_stream(params)
        aggregated_response = await aggregate_stream(stream)
        logger.info(f"Successfully aggregated stream for request ID: {aggregated_response.id}")
        return aggregated_response.model_dump(exclude_none=True)

    except httpx.HTTPStatusError as e:
        error_body = "<Could not read error body>"
        try:
            error_body = e.response.json() if e.response else str(e)
        except Exception:
            try:
                 error_body = e.response.text if e.response else str(e)
            except Exception:
                 pass # Keep the default message
        logger.error(f"API returned an error: {e.status_code} - {error_body}")
        return {"error": f"API Error: {e.status_code}", "details": error_body}
    except httpx.TimeoutException:
        logger.error("API request timed out.")
        return {"error": "Request timed out"}
    except httpx.RequestError as e:
        logger.error(f"Network error connecting to API: {e}")
        return {"error": f"Network error: {e}"}
    except ValueError as e:
        logger.error(f"Data validation or aggregation error: {e}")
        return {"error": f"Data error: {e}"}
    except Exception as e:
        logger.exception("An unexpected error occurred in chat_completion tool")
        return {"error": f"An unexpected server error occurred: {str(e)}"}

@mcp.on_shutdown
async def shutdown():
    """Cleanly shuts down the API client when the MCP server stops."""
    if api_client:
        await api_client.close()
        logger.info("Jina DeepSearch API client closed.")

if __name__ == "__main__":
    # Note: FastMCP's run() method handles the ASGI server setup.
    # You might need to run this with uvicorn directly for more control:
    # uvicorn main:mcp.app --host 0.0.0.0 --port 8000
    logger.info("Starting Jina DeepSearch MCP Server")
    # mcp.run() # This is a simplified way, might not exist or work as expected.
    # Use uvicorn programmatically or via command line.
    import uvicorn
    uvicorn.run(mcp.app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
