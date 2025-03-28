from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal

# --- Base Models from Type Definitions ---

class ImageUrl(BaseModel):
    """Represents an image URL, potentially a data URI."""
    url: str = Field(..., description="URL of the image (http(s):// or data:image/...)")

class FileUrl(BaseModel):
    """Represents a file data URI."""
    url: str = Field(..., description="Data URI of the file (data:[<mediatype>][;base64],<data>). Max 10MB.")

class MessageContentPart(BaseModel):
    """Represents a part of a message content, which can be text or an image/file data URI."""
    type: Literal['text', 'image_url', 'file_url'] = Field(..., description="Type of content part ('text', 'image_url', 'file_url').")
    text: Optional[str] = Field(None, description="Text content.")
    image_url: Optional[ImageUrl] = Field(None, description="Image URL object.")
    file_url: Optional[FileUrl] = Field(None, description="File data URI object.")

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant'] = Field(..., description="Role of the message author ('user' or 'assistant').")
    content: Union[str, List[MessageContentPart]] = Field(..., description="Content of the message. Can be simple text or a list of content parts for multimodal input.")

class UrlCitationAnnotation(BaseModel):
    """Details of a URL citation within the response content."""
    title: str = Field(..., description="Title of the cited web page.")
    exactQuote: str = Field(..., description="The exact quote from the source used in the answer.")
    url: str = Field(..., description="URL of the source.")
    dateTime: str = Field(..., description="Timestamp when the content was accessed or published.")

class Annotation(BaseModel):
    """Annotation object within the response delta/message."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitationAnnotation] = Field(None, description="Details if the annotation type is 'url_citation'.")

class ResponseMessage(BaseModel):
    """Represents the assistant's message in the response (non-streamed)."""
    role: str = Field(..., description="Typically 'assistant'.")
    content: Optional[str] = Field(None, description="The main textual content of the response.")
    type: Optional[str] = Field(None, description="Type indicator, e.g., 'text'.")
    annotations: Optional[List[Annotation]] = Field(None, description="List of annotations, like URL citations.")

class ResponseDelta(BaseModel):
    """Represents the delta in a streamed response chunk."""
    role: Optional[str] = Field(None, description="Typically 'assistant'.")
    content: Optional[str] = Field(None, description="The partial content of the response chunk.")
    type: Optional[str] = Field(None, description="Type indicator, e.g., 'text'.")
    # Note: Annotations might appear in the final chunk or specific chunks in streaming
    annotations: Optional[List[Annotation]] = Field(None, description="List of annotations, like URL citations.")


# --- Input Model for chat_completion Tool ---

class DeepSearchChatInput(BaseModel):
    """Input model for the DeepSearch chat completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use. Currently only 'jina-deepsearch-v1' is supported.")
    stream: bool = Field(True, description="Whether to stream back partial progress and the final answer. Recommended to be true to avoid timeouts.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains reasoning effort. Supported values: 'low', 'medium', 'high'. Overridden by budget_tokens or max_attempts.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides reasoning_effort.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Overrides reasoning_effort.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces further thinking/search steps even for seemingly trivial queries.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="JSON schema to ensure the final answer matches the structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        # Ensure default values are used correctly
        use_enum_values = True

# --- Output Models (Based on OpenAI Schema Compatibility) ---

class UsageInfo(BaseModel):
    """Token usage information for the request."""
    prompt_tokens: int
    completion_tokens: Optional[int] = None # May not be present in all chunks
    total_tokens: int

# Non-Streaming Output
class DeepSearchChatOutputChoice(BaseModel):
    index: int
    message: ResponseMessage
    finish_reason: Optional[str] = None # e.g., 'stop', 'length'

class DeepSearchChatOutput(BaseModel):
    """Structure of the non-streaming response from DeepSearch."""
    id: str
    object: str = "chat.completion"
    created: int # Unix timestamp
    model: str
    choices: List[DeepSearchChatOutputChoice]
    usage: UsageInfo
    visitedUrls: Optional[List[str]] = Field(None, description="List of URLs visited during the search process.")
    searchQueries: Optional[List[str]] = Field(None, description="List of search queries executed.")

# Streaming Output
class DeepSearchChatChunkChoice(BaseModel):
    index: int
    delta: ResponseDelta
    finish_reason: Optional[str] = None # Usually in the last chunk

class DeepSearchChatChunk(BaseModel):
    """Structure of a streaming chunk from DeepSearch."""
    id: str
    object: str = "chat.completion.chunk"
    created: int # Unix timestamp
    model: str
    choices: List[DeepSearchChatChunkChoice]
    usage: Optional[UsageInfo] = None # Usually in the last chunk
    visitedUrls: Optional[List[str]] = Field(None, description="List of URLs visited during the search process, often in the final chunk.")
    searchQueries: Optional[List[str]] = Field(None, description="List of search queries executed, often in the final chunk.")

