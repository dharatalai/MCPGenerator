from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union, Literal

# Type Definitions from Implementation Plan

class MessageContentPart(BaseModel):
    """Represents a part of the message content, which can be text or an image/file URL."""
    type: Literal['text', 'image_url', 'file_url'] = Field(..., description="Type of content part ('text', 'image_url', 'file_url').")
    text: Optional[str] = Field(None, description="The text content, if type is 'text'.")
    image_url: Optional[Dict[str, str]] = Field(None, description="The image URL (data URI), if type is 'image_url'. Structure: {'url': 'data:image/...'}")
    file_url: Optional[Dict[str, str]] = Field(None, description="The file URL (data URI), if type is 'file_url'. Structure: {'url': 'data:application/...'}")

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant', 'system'] = Field(..., description="The role of the author ('user', 'assistant', or 'system').")
    content: Union[str, List[MessageContentPart]] = Field(..., description="The content of the message. Can be a simple string or a list of content parts for multimodal input.")

class URLCitation(BaseModel):
    """Details of a URL citation within the response."""
    title: Optional[str] = Field(None, description="Title of the cited page.")
    exactQuote: Optional[str] = Field(None, alias="exactQuote", description="The exact quote cited from the source.")
    url: str = Field(..., description="URL of the cited source.")
    dateTime: Optional[str] = Field(None, alias="dateTime", description="Timestamp related to the citation.")

class Annotation(BaseModel):
    """Annotation associated with the response content, e.g., a URL citation."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[URLCitation] = Field(None, description="Details if the annotation is a URL citation.")

class Delta(BaseModel):
    """The delta content for a streaming chunk."""
    role: Optional[Literal['assistant']] = Field(None, description="Role associated with the chunk ('assistant').")
    content: Optional[str] = Field(None, description="The text content of the chunk. May include XML tags like <think> for reasoning steps.")
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').")
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations for the content chunk.")

class ChoiceChunk(BaseModel):
    """Represents a choice in a streaming response chunk."""
    index: int = Field(..., description="Index of the choice.")
    delta: Delta = Field(..., description="The content delta for a streaming chunk.")
    logprobs: Optional[Any] = Field(None, description="Log probability information (currently null).")
    finish_reason: Optional[str] = Field(None, description="Reason the generation finished (e.g., 'stop').")

class ChoiceResponse(BaseModel):
    """Represents a choice in a non-streaming response."""
    index: int = Field(..., description="Index of the choice.")
    message: Message = Field(..., description="The full message for a non-streaming response.")
    logprobs: Optional[Any] = Field(None, description="Log probability information (currently null).")
    finish_reason: Optional[str] = Field(None, description="Reason the generation finished (e.g., 'stop').")

class Usage(BaseModel):
    """Token usage statistics for the request."""
    prompt_tokens: int = Field(..., description="Tokens used by the prompt.")
    completion_tokens: int = Field(..., description="Tokens generated for the completion.")
    total_tokens: int = Field(..., description="Total tokens used.")

class DeepSearchChatChunk(BaseModel):
    """Structure of a single chunk received during streaming."""
    id: str = Field(..., description="Unique identifier for the chat completion chunk.")
    object: str = Field(..., description="Object type, e.g., 'chat.completion.chunk'.")
    created: int = Field(..., description="Timestamp of creation.")
    model: str = Field(..., description="Model used.")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint.")
    choices: List[ChoiceChunk] = Field(..., description="List of choices, usually one.")
    usage: Optional[Usage] = Field(None, description="Token usage (present in the final chunk).")
    visitedURLs: Optional[List[str]] = Field(None, description="URLs visited during the search process (present in the final chunk).")
    readURLs: Optional[List[str]] = Field(None, description="URLs read during the search process (present in the final chunk).") # Added based on plan description
    numURLs: Optional[int] = Field(None, description="Number of URLs (present in the final chunk).") # Added based on plan description

class DeepSearchChatResponse(BaseModel):
    """Structure of the response received for non-streaming requests."""
    id: str = Field(..., description="Unique identifier for the chat completion.")
    object: str = Field(..., description="Object type, e.g., 'chat.completion'.")
    created: int = Field(..., description="Timestamp of creation.")
    model: str = Field(..., description="Model used.")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint.")
    choices: List[ChoiceResponse] = Field(..., description="List of choices, usually one.")
    usage: Usage = Field(..., description="Token usage statistics.")
    visitedURLs: Optional[List[str]] = Field(None, description="URLs visited during the search process.")
    readURLs: Optional[List[str]] = Field(None, description="URLs read during the search process.")
    numURLs: Optional[int] = Field(None, description="Number of URLs.")

# Input Model Definition

class DeepSearchChatRequest(BaseModel):
    """Request model for the Jina DeepSearch chat completions endpoint."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation so far. Supports text, images (webp, png, jpeg as data URI), and files (txt, pdf as data URI up to 10MB).")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use. Currently 'jina-deepsearch-v1'.")
    stream: bool = Field(True, description="Whether to stream back partial progress (reasoning steps and final answer). Strongly recommended to be true to avoid timeouts.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains effort on reasoning. Supported values: 'low', 'medium', 'high'. Overridden by budget_tokens or max_attempts.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides reasoning_effort.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Overrides reasoning_effort.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces the model to take further thinking/search steps even for trivial queries.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="JSON schema to ensure the final answer matches the structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        use_enum_values = True # Ensure Literal values are handled correctly
