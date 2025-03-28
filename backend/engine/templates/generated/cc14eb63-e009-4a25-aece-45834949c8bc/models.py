from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal

# --- Message Content Parts ---

class TextMessageContentPart(BaseModel):
    """Text content part."""
    type: Literal['text'] = Field(..., description="Type identifier.")
    text: str = Field(..., description="The text content.")

class ImageUrl(BaseModel):
    """URL structure for image content."""
    url: str = Field(..., description="Data URI for the image (e.g., 'data:image/jpeg;base64,...').")

class ImageMessageContentPart(BaseModel):
    """Image content part using data URI."""
    type: Literal['image_url'] = Field(..., description="Type identifier.")
    image_url: ImageUrl = Field(..., description="The image URL object containing the data URI.")

class FileUrl(BaseModel):
    """URL structure for file content."""
    url: str = Field(..., description="Data URI for the file (e.g., 'data:text/plain;base64,...', 'data:application/pdf;base64,...').")

class FileMessageContentPart(BaseModel):
    """File content part using data URI."""
    type: Literal['file_url'] = Field(..., description="Type identifier.")
    file_url: FileUrl = Field(..., description="The file URL object containing the data URI.")

MessageContentPart = Union[TextMessageContentPart, ImageMessageContentPart, FileMessageContentPart]

# --- Message --- 

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant'] = Field(..., description="The role of the author ('user' or 'assistant').")
    content: Union[str, List[MessageContentPart]] = Field(..., description="The content of the message. Can be a simple string or a list of content parts for multi-modal input.")

# --- Input Model --- 

class DeepSearchChatInput(BaseModel):
    """Input model for the Jina DeepSearch chat completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use. Currently only 'jina-deepsearch-v1' is available.")
    stream: bool = Field(True, description="Whether to stream back partial progress. Recommended to keep true.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constraint on reasoning effort ('low', 'medium', 'high').")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the entire DeepSearch process.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem.")
    no_direct_answer: bool = Field(False, description="Force the model to perform search/thinking steps.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="JSON schema to ensure the final answer conforms to the specified structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        # Ensure default values are excluded if not provided
        exclude_defaults = True 

# --- Response Models (Based on OpenAI Schema) ---

class UrlCitation(BaseModel):
    """Details of a URL citation within the response."""
    title: Optional[str] = Field(None, description="Title of the cited page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source.")
    url: str = Field(..., description="URL of the source.")
    dateTime: Optional[str] = Field(None, description="Timestamp associated with the citation.")

class Annotation(BaseModel):
    """Annotation associated with the response content."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitation] = Field(None, description="Details if the annotation is a URL citation.")

class Delta(BaseModel):
    """The delta content for a streaming chunk."""
    role: Optional[Literal['assistant']] = Field(None, description="Role of the author (usually 'assistant').")
    content: Optional[str] = Field(None, description="The content delta. Can contain text or XML tags like <think> for reasoning steps.")
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').")
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations associated with this delta.")

class LogProbs(BaseModel):
    """Log probability information (typically null for DeepSearch)."""
    pass # Usually null or empty for this API

class ChoiceChunk(BaseModel):
    """A choice within a streaming response chunk."""
    index: int = Field(..., description="Index of the choice.")
    delta: Delta = Field(..., description="The content delta.")
    finish_reason: Optional[str] = Field(None, description="Reason the stream finished (e.g., 'stop', 'length').")
    logprobs: Optional[LogProbs] = Field(None, description="Log probability information.")

class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = Field(..., description="Tokens in the prompt.")
    completion_tokens: int = Field(..., description="Tokens in the completion.")
    total_tokens: int = Field(..., description="Total tokens used.")

class DeepSearchChatResponseChunk(BaseModel):
    """Schema for a chunk in a streaming chat completion response."""
    id: str = Field(..., description="Unique identifier for the chunk.")
    object: str = Field(..., description="Object type, typically 'chat.completion.chunk'.")
    created: int = Field(..., description="Unix timestamp of when the chunk was created.")
    model: str = Field(..., description="Model used for the completion.")
    choices: List[ChoiceChunk] = Field(..., description="List of choices in the chunk.")
    usage: Optional[Usage] = Field(None, description="Token usage stats (usually only in the final chunk).")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint.")
    visited_urls: Optional[List[str]] = Field(None, description="List of visited URLs (usually only in the final chunk).")

class Choice(BaseModel):
    """A choice in a non-streaming response."""
    index: int = Field(..., description="Index of the choice.")
    message: Message = Field(..., description="The assistant's response message.")
    finish_reason: Optional[str] = Field(None, description="Reason the completion finished.")
    logprobs: Optional[LogProbs] = Field(None, description="Log probability information.")

class DeepSearchChatResponse(BaseModel):
    """Schema for a non-streaming chat completion response."""
    id: str = Field(..., description="Unique identifier for the response.")
    object: str = Field(..., description="Object type, typically 'chat.completion'.")
    created: int = Field(..., description="Unix timestamp of when the response was created.")
    model: str = Field(..., description="Model used for the completion.")
    choices: List[Choice] = Field(..., description="List of completion choices.")
    usage: Optional[Usage] = Field(None, description="Token usage statistics.")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint.")
    visited_urls: Optional[List[str]] = Field(None, description="List of URLs visited during the search process.")
