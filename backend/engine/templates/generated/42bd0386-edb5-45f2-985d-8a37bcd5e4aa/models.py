from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union, Literal


class MessageContentPart(BaseModel):
    """Represents a part of the content in a message, can be text or image/document URI."""
    type: Literal["text", "image_url", "document_url"] = Field(..., description="Type of content part, e.g., 'text', 'image_url', 'document_url'")
    text: Optional[str] = Field(None, description="The text content.")
    image_url: Optional[Dict[str, str]] = Field(None, description="Dictionary containing 'url' key with data URI for image (webp, png, jpeg).")
    document_url: Optional[Dict[str, str]] = Field(None, description="Dictionary containing 'url' key with data URI for document (txt, pdf, max 10MB).")

    class Config:
        extra = 'forbid' # Ensure no unexpected fields

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal["user", "assistant"] = Field(..., description="The role of the message author ('user' or 'assistant').")
    content: Union[str, List[MessageContentPart]] = Field(..., description="The content of the message. Can be a simple string or a list of content parts for multimodal input.")

    class Config:
        extra = 'forbid'

class DeepSearchChatInput(BaseModel):
    """Input model for the DeepSearch chat_completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history. Must include at least one user message. Supports text, images (webp, png, jpeg as data URIs), and files (txt, pdf as data URIs up to 10MB).")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use.")
    stream: bool = Field(True, description="Whether to stream back partial progress. If true, delivers events as Server-Sent Events. Strongly recommended to be true to avoid timeouts for long-running requests.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains effort on reasoning. Supported values: 'low', 'medium', 'high'. Default is 'medium'. Lower effort can lead to faster responses but potentially less depth.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides 'reasoning_effort'. Larger budgets can improve quality for complex queries.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Allows trying different reasoning approaches. Overrides 'reasoning_effort'.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces the model to perform thinking/search steps even for seemingly trivial queries. Useful when certainty of needing deep search is high.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk, sorted by relevance.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="Enables structured output, ensuring the final answer matches the provided JSON schema.")
    good_domains: Optional[List[str]] = Field(None, description="A list of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="A list of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="A list of domains to exclusively include in content retrieval.")

    class Config:
        extra = 'forbid'

# Placeholder models for response types - structure might vary based on actual API output
class DeepSearchUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class DeepSearchChoiceDelta(BaseModel):
    role: Optional[Literal['assistant']] = None
    content: Optional[str] = None

class DeepSearchChoice(BaseModel):
    index: int
    delta: Optional[DeepSearchChoiceDelta] = None # For streaming
    message: Optional[Message] = None # For non-streaming
    finish_reason: Optional[str] = None
    urls: Optional[List[str]] = None

class DeepSearchResponseChunk(BaseModel):
    """Represents a chunk of the response when streaming."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[DeepSearchChoice]
    usage: Optional[DeepSearchUsage] = None # Usually present in the final chunk

class DeepSearchResponse(BaseModel):
    """Represents the full response when not streaming."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[DeepSearchChoice]
    usage: DeepSearchUsage
