from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
import time

# --- Type Definitions from Plan ---

class MessageContentPart(BaseModel):
    """Represents a part of a multimodal message content."""
    type: str # e.g., 'text', 'image_url'
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None # e.g., {"url": "data:image/jpeg;base64,..."}

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant', 'system'] = Field(..., description="The role of the message author.")
    content: Union[str, List[MessageContentPart]] = Field(..., description="The content of the message. Can be plain text or a list for multimodal content.")
    name: Optional[str] = Field(None, description="An optional name for the participant.")

class UrlCitation(BaseModel):
    """Details of a URL citation within the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source.")
    url: str = Field(..., description="The URL of the source.")
    dateTime: Optional[str] = Field(None, description="Timestamp associated with the citation.")

class Annotation(BaseModel):
    """Annotation within the response content."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitation] = Field(None, description="Details if the annotation is a URL citation.")

# --- Input Model ---

class DeepSearchChatInput(BaseModel):
    """Input model for the chat_completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history. The last message should be the user's query.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use.")
    stream: bool = Field(True, description="Whether to stream back partial progress. Strongly recommended.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains reasoning effort ('low', 'medium', 'high').")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides reasoning_effort.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Overrides reasoning_effort.")
    no_direct_answer: bool = Field(False, description="Forces search/thinking steps even for seemingly trivial queries.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="Enables structured output matching a supplied JSON schema.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        use_enum_values = True # Ensure Literal values are sent as strings

# --- Output Models (Mirroring OpenAI Schema) ---

# Streaming Response Models
class DeepSearchChatCompletionChoiceDelta(BaseModel):
    """Delta content for a streaming chat completion chunk."""
    content: Optional[str] = None
    role: Optional[Literal['assistant']] = None
    # DeepSearch might include other fields like annotations here
    annotations: Optional[List[Annotation]] = None

class DeepSearchChatCompletionChunkChoice(BaseModel):
    """A choice within a streaming chat completion chunk."""
    delta: DeepSearchChatCompletionChoiceDelta
    index: int
    finish_reason: Optional[Literal['stop', 'length', 'content_filter', 'tool_calls', 'error']] = None
    # DeepSearch might include logprobs here

class DeepSearchUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0

class DeepSearchChatCompletionChunk(BaseModel):
    """Represents a chunk of the streaming chat completion response."""
    id: str
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[DeepSearchChatCompletionChunkChoice]
    usage: Optional[DeepSearchUsage] = None # Usually present only in the last chunk
    # DeepSearch might include system_fingerprint or other fields

# Non-Streaming Response Models
class DeepSearchChatCompletionChoice(BaseModel):
    """A choice in a non-streaming chat completion response."""
    message: Message
    index: int
    finish_reason: Optional[Literal['stop', 'length', 'content_filter', 'tool_calls', 'error']] = None
    # DeepSearch might include logprobs or annotations here

class DeepSearchChatCompletion(BaseModel):
    """Represents the full response for a non-streaming chat completion."""
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[DeepSearchChatCompletionChoice]
    usage: Optional[DeepSearchUsage] = None
    # DeepSearch might include system_fingerprint or other fields
