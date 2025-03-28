from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Type Definitions from Implementation Plan ---

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: str = Field(..., description="The role of the message author ('user' or 'assistant').")
    content: str = Field(..., description="The content of the message. Can be plain text or a data URI for images/documents.")

class UrlCitation(BaseModel):
    """Details of a URL citation within the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source.")
    url: str = Field(..., description="The URL of the citation.")
    dateTime: Optional[str] = Field(None, description="Timestamp associated with the citation.")

class Annotation(BaseModel):
    """Annotation associated with the response content."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitation] = Field(None, description="Details if the annotation is a URL citation.")

class Delta(BaseModel):
    """Represents the change in content for a streamed chunk (or the full content in the final chunk/non-streamed response)."""
    role: Optional[str] = Field(None, description="The role of the message author, typically 'assistant'. Appears in the first chunk.")
    content: Optional[str] = Field(None, description="The text content chunk.")
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').")
    annotations: Optional[List[Annotation]] = Field(None, description="List of annotations related to the content.")

class Choice(BaseModel):
    """Represents a single response choice."""
    index: int = Field(..., description="Index of the choice.")
    delta: Optional[Delta] = Field(None, description="The message content and annotations (used in streaming).")
    message: Optional[Message] = Field(None, description="The full message (used in non-streaming responses, similar structure to Delta but within 'message').")
    logprobs: Optional[Any] = Field(None, description="Log probabilities (currently null in example).")
    finish_reason: Optional[str] = Field(None, description="Reason the generation finished (e.g., 'stop').")

class Usage(BaseModel):
    """Token usage statistics for the request."""
    prompt_tokens: Optional[int] = Field(None, description="Tokens used by the prompt.") # Optional because it might not be in every chunk
    completion_tokens: Optional[int] = Field(None, description="Tokens generated for the completion.") # Optional
    total_tokens: Optional[int] = Field(None, description="Total tokens used in the entire process.") # Optional

class DeepSearchResponse(BaseModel):
    """The overall structure of the response from the DeepSearch API (can represent a chunk or a full response)."""
    id: str = Field(..., description="Unique identifier for the response/chunk.")
    object: str = Field(..., description="Type of object (e.g., 'chat.completion' or 'chat.completion.chunk').")
    created: int = Field(..., description="Timestamp of creation (Unix epoch).")
    model: str = Field(..., description="Model used for the response.")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint.")
    choices: List[Choice] = Field(..., description="List of response choices (usually one).")
    usage: Optional[Usage] = Field(None, description="Token usage information (present in the final chunk/response).")
    visitedURLs: Optional[List[str]] = Field(None, description="List of URLs visited during the search process (present in final chunk/response).", alias="visitedURLs") # Alias for camelCase
    readURLs: Optional[List[str]] = Field(None, description="List of URLs read during the search process (present in final chunk/response).", alias="readURLs") # Alias for camelCase
    numURLs: Optional[int] = Field(None, description="Total number of unique URLs encountered (present in final chunk/response).", alias="numURLs") # Alias for camelCase

    class Config:
        allow_population_by_field_name = True # Allow using visitedURLs etc directly

# --- Input Model Definition ---

class DeepSearchChatParams(BaseModel):
    """Input parameters for the Jina DeepSearch chat completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history. The last message should be the user's query. Supports text, image (webp, png, jpeg), and document (txt, pdf) content encoded as data URIs (up to 10MB).")
    model: str = Field(default="jina-deepsearch-v1", description="ID of the model to use.")
    stream: bool = Field(default=True, description="Whether to stream back partial progress. If disabled, the request might time out for long-running queries. Strongly recommended to keep enabled (default). The MCP tool will handle aggregation if streaming is used.")
    reasoning_effort: Optional[str] = Field(None, description="Constrains effort on reasoning. Supported values: 'low', 'medium', 'high'. Default: 'medium'.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides 'reasoning_effort'.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Overrides 'reasoning_effort'.")
    no_direct_answer: Optional[bool] = Field(None, description="Forces the model to take further thinking/search steps even for trivial queries. Default: false.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="A JSON schema object to ensure the final answer matches the supplied schema.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        extra = 'ignore' # Ignore any extra fields sent in the request
