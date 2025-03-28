from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

# --- Input Models ---

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant', 'system'] = Field(..., description="The role of the message author ('user', 'assistant', or 'system').")
    content: str = Field(..., description="The content of the message. Can be plain text or a data URI for images/documents (e.g., 'data:image/png;base64,...', 'data:application/pdf;base64,...').")

class DeepSearchInput(BaseModel):
    """Input model for the DeepSearch chat completion request."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history, including the latest user query. Supports text and multimodal content (images/documents as data URIs).")
    model: str = Field(default="jina-deepsearch-v1", description="ID of the model to use. Currently only 'jina-deepsearch-v1' is supported.")
    stream: bool = Field(default=True, description="Whether to stream back partial progress and the final answer using server-sent events. Recommended to be true to avoid timeouts for long-running queries.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field(default="medium", description="Constrains the reasoning effort. Supported values: 'low', 'medium', 'high'. Affects response time and token usage.")
    budget_tokens: Optional[int] = Field(default=None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides 'reasoning_effort'.")
    max_attempts: Optional[int] = Field(default=None, description="Maximum number of retries for solving the problem using different reasoning approaches. Overrides 'reasoning_effort'.")
    no_direct_answer: bool = Field(default=False, description="Forces the model to perform search/thinking steps even for seemingly trivial queries.")
    max_returned_urls: Optional[int] = Field(default=None, description="Maximum number of URLs to include in the final answer/chunk, sorted by relevance.")
    structured_output: Optional[Dict[str, Any]] = Field(default=None, description="JSON schema to ensure the final answer conforms to the specified structure.")
    good_domains: Optional[List[str]] = Field(default=None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(default=None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(default=None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        # Ensure None values are not included in the output dict if not set
        exclude_none = True

# --- Output Models ---

class UrlCitation(BaseModel):
    """Details of a URL citation used in the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source that supports the answer.")
    url: Optional[str] = Field(None, description="URL of the source.")
    dateTime: Optional[str] = Field(None, description="Timestamp associated with the citation.")

class Annotation(BaseModel):
    """Annotation associated with the response content, like citations."""
    type: Optional[str] = Field(None, description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitation] = Field(None, description="Details if the annotation is a URL citation.")

class Delta(BaseModel):
    """The content delta in a streamed chunk."""
    role: Optional[Literal['assistant']] = Field(None, description="The role of the message author, typically 'assistant'.")
    content: Optional[str] = Field(None, description="The text content of the chunk.")
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').") # Note: Jina API might not use 'type' here
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations related to the content.")

class Choice(BaseModel):
    """A single response choice (streaming or non-streaming)."""
    index: int = Field(..., description="Index of the choice.")
    delta: Optional[Delta] = Field(None, description="The content delta for this choice (used in streaming).")
    message: Optional[Message] = Field(None, description="The full message object (used in non-streaming).")
    logprobs: Optional[Any] = Field(None, description="Log probabilities (currently null in Jina API).")
    finish_reason: Optional[str] = Field(None, description="Reason the model stopped generating tokens (e.g., 'stop', 'length', 'error').")

class Usage(BaseModel):
    """Token usage statistics for the request."""
    prompt_tokens: int = Field(..., description="Tokens used in the prompt/reasoning process.")
    # Note: Jina DeepSearch API currently only provides prompt_tokens in usage
    completion_tokens: Optional[int] = Field(None, description="Tokens generated for the completion (Not provided by Jina API).")
    total_tokens: Optional[int] = Field(None, description="Total tokens (Not provided by Jina API).")

class DeepSearchChunk(BaseModel):
    """Represents a chunk received during a streaming response."""
    id: str = Field(..., description="A unique identifier for the chat completion chunk.")
    object: str = Field(..., description="The object type, which is always 'chat.completion.chunk'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chat completion chunk was created.")
    model: str = Field(..., description="The model to generate the completion.")
    choices: List[Choice] = Field(..., description="A list of chat completion choices. Can contain more than one if n > 1, but typically 1 for Jina.")
    usage: Optional[Usage] = Field(None, description="An object describing the token usage statistics for the completion (usually present in the final chunk).")
    system_fingerprint: Optional[str] = Field(None, description="This fingerprint represents the backend configuration that the model runs with.")
    # Jina specific fields that might appear in the last chunk
    visited_urls: Optional[List[str]] = Field(None, description="List of URLs visited during the search process (usually in the final chunk).")

class DeepSearchResponse(BaseModel):
    """Represents the full response for a non-streaming request."""
    id: str = Field(..., description="A unique identifier for the chat completion.")
    object: str = Field(..., description="The object type, which is always 'chat.completion'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str = Field(..., description="The model used for the chat completion.")
    choices: List[Choice] = Field(..., description="A list of chat completion choices.")
    usage: Usage = Field(..., description="Usage statistics for the completion request.")
    system_fingerprint: Optional[str] = Field(None, description="This fingerprint represents the backend configuration that the model runs with.")
    # Jina specific fields
    visited_urls: Optional[List[str]] = Field(None, description="List of URLs visited during the search process.")
