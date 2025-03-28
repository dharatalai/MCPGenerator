from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

# --- Type Definitions from Plan ---

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant'] = Field(..., description="The role of the message author ('user' or 'assistant').")
    content: str = Field(..., description="The content of the message. Can be plain text or a data URI for images/files.")

class UrlCitation(BaseModel):
    """Details of a URL citation used in the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source.")
    url: str = Field(..., description="URL of the source.")
    dateTime: Optional[str] = Field(None, description="Timestamp associated with the citation (ISO format likely).")

class Annotation(BaseModel):
    """Annotation associated with the message content."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitation] = Field(None, description="Details if the annotation is a URL citation.")

class ResponseMessage(BaseModel):
    """Represents the message content in the response."""
    role: Optional[Literal['assistant']] = Field(None, description="Role of the message author (always 'assistant' in response).") # Added based on OpenAI schema
    content: Optional[str] = Field(None, description="The textual content of the response message.") # Optional for streaming delta
    type: Optional[str] = Field(None, description="Type of the content (e.g., 'text').")
    annotations: Optional[List[Annotation]] = Field(None, description="List of annotations, like URL citations.")

class Choice(BaseModel):
    """Represents one possible completion choice."""
    index: int = Field(..., description="Index of the choice.")
    delta: Optional[ResponseMessage] = Field(None, description="The message content delta (used in streaming).")
    message: Optional[ResponseMessage] = Field(None, description="The complete message content (used in non-streaming or final chunk).")
    logprobs: Optional[Any] = Field(None, description="Log probability information (null in example).")
    finish_reason: Optional[str] = Field(None, description="Reason the generation finished (e.g., 'stop').") # Optional as it might not be in every chunk

class Usage(BaseModel):
    """Token usage statistics for the request."""
    prompt_tokens: Optional[int] = Field(None, description="Tokens in the input prompt.")
    completion_tokens: Optional[int] = Field(None, description="Tokens in the generated completion.") # Added based on OpenAI schema
    total_tokens: Optional[int] = Field(None, description="Total tokens used in the request.") # Added based on OpenAI schema

# --- Input Model Definition ---

class DeepSearchChatInput(BaseModel):
    """Input model for the DeepSearch chat_completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history between the user and the assistant. Can include text, images (webp, png, jpeg encoded as data URI), or files (txt, pdf encoded as data URI, up to 10MB).")
    model: str = Field(..., description="ID of the DeepSearch model to use (e.g., 'jina-deepsearch-v1').")
    stream: Optional[bool] = Field(True, description="Whether to stream back partial progress using server-sent events. Strongly recommended to be true to avoid timeouts. Defaults to true.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field('medium', description="Constrains effort on reasoning. Supported values: 'low', 'medium', 'high'. Defaults to 'medium'.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides reasoning_effort. Larger budgets may improve quality for complex queries.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Allows trying different reasoning approaches. Overrides reasoning_effort.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces the model to perform search/thinking steps even for seemingly trivial queries. Defaults to false.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer, sorted by relevance.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="A JSON schema object to ensure the final answer conforms to the specified structure.")
    good_domains: Optional[List[str]] = Field(None, description="A list of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="A list of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="A list of domains to exclusively include in content retrieval.")

    class Config:
        # Define example for documentation generation if needed
        schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "What is the capital of France?"}
                ],
                "model": "jina-deepsearch-v1",
                "stream": False
            }
        }

# --- Return Type Definition ---

class DeepSearchChatOutput(BaseModel):
    """The final aggregated response from the DeepSearch API, containing the generated answer, choices, usage statistics, and visited/read URLs. If streaming was enabled, this represents the final message combining all chunks."""
    id: str = Field(..., description="A unique identifier for the chat completion.")
    object: str = Field(..., description="The object type, which is always 'chat.completion' or 'chat.completion.chunk'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str = Field(..., description="The model used for the chat completion.")
    choices: List[Choice] = Field(..., description="A list of chat completion choices.")
    usage: Optional[Usage] = Field(None, description="Usage statistics for the completion request.")
    visited_urls: Optional[List[str]] = Field(None, description="List of URLs visited during the search process.") # Specific to DeepSearch
    read_urls: Optional[List[str]] = Field(None, description="List of URLs read during the search process.") # Specific to DeepSearch

    class Config:
        # Define example for documentation generation if needed
        schema_extra = {
            "example": {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "jina-deepsearch-v1",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "The capital of France is Paris.",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url_citation": {
                                        "url": "https://en.wikipedia.org/wiki/Paris",
                                        "title": "Paris - Wikipedia"
                                    }
                                }
                            ]
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 9,
                    "completion_tokens": 12,
                    "total_tokens": 21
                },
                "visited_urls": ["https://en.wikipedia.org/wiki/Paris"],
                "read_urls": ["https://en.wikipedia.org/wiki/Paris"]
            }
        }
