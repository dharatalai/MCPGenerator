from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal, Union

# --- Type Definitions from Plan ---

class ChatMessage(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant', 'system'] = Field(..., description="The role of the message author.")
    content: Union[str, List[Dict[str, Any]]] = Field(..., description="The content of the message. Can be text or a list for multimodal inputs (e.g., text and image URLs or data URIs).")

class URLCitation(BaseModel):
    """Details of a URL citation within the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, alias="exactQuote", description="The exact quote from the source.")
    url: str = Field(..., description="URL of the source.")
    dateTime: Optional[str] = Field(None, alias="dateTime", description="Timestamp associated with the citation.")

class Annotation(BaseModel):
    """Annotation associated with the content, like a citation."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[URLCitation] = Field(None, description="Details if the annotation is a URL citation.")

class ChoiceDelta(BaseModel):
    """The delta content for a streaming choice."""
    role: Optional[Literal['assistant']] = Field(None, description="Role of the author ('assistant').")
    content: Optional[str] = Field(None, description="The text content delta.")
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').")
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations related to the content delta.")

class ResponseMessage(BaseModel):
    """The complete message content for a non-streaming choice."""
    role: str = Field(..., description="Role of the author ('assistant').")
    content: Optional[str] = Field(None, description="The full text content.")
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').")
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations related to the content.")

# --- Input Model ---

class DeepSearchChatInput(BaseModel):
    """Input model for the Jina DeepSearch chat completion tool."""
    messages: List[ChatMessage] = Field(..., description="A list of messages comprising the conversation history.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use.")
    stream: bool = Field(True, description="Whether to stream back partial progress using server-sent events. Recommended to keep enabled to avoid timeouts.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains effort on reasoning. 'low', 'medium', or 'high'. Lower effort can be faster and use fewer tokens.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides reasoning_effort.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Allows different reasoning approaches. Overrides reasoning_effort.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces the model to take further thinking/search steps even for seemingly trivial queries.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk, sorted by relevance.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="JSON schema to ensure the final answer matches the structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        # Ensure Pydantic uses the field names, not aliases, for serialization
        by_alias = False

# --- Output Models (Inferred from OpenAI Schema & Plan) ---

class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: Optional[int] = Field(None)
    completion_tokens: Optional[int] = Field(None)
    total_tokens: Optional[int] = Field(None)

class VisitedUrl(BaseModel):
    """Details of a URL visited during the search process."""
    url: str
    title: Optional[str] = None
    # Add other fields if the API provides them

class DeepSearchChunkChoice(BaseModel):
    """A single choice within a streaming chunk."""
    index: int
    delta: ChoiceDelta
    finish_reason: Optional[str] = None
    # Jina specific fields might appear here
    visited_urls: Optional[List[VisitedUrl]] = Field(None, description="URLs visited during the search process, often included in the final chunk.")

class DeepSearchChunk(BaseModel):
    """Represents a chunk of data received during streaming."""
    id: str
    object: str # e.g., 'chat.completion.chunk'
    created: int
    model: str
    choices: List[DeepSearchChunkChoice]
    usage: Optional[Usage] = Field(None, description="Usage statistics, often included in the final chunk.")
    # Jina specific fields might appear here
    search_summary: Optional[Dict[str, Any]] = Field(None, description="Summary information about the search process, often in the final chunk.")

class DeepSearchResponseChoice(BaseModel):
    """A single choice in a non-streaming response."""
    index: int
    message: ResponseMessage
    finish_reason: Optional[str] = None
    # Jina specific fields might appear here
    visited_urls: Optional[List[VisitedUrl]] = Field(None, description="URLs visited during the search process.")

class DeepSearchResponse(BaseModel):
    """Represents the complete response for a non-streaming request."""
    id: str
    object: str # e.g., 'chat.completion'
    created: int
    model: str
    choices: List[DeepSearchResponseChoice]
    usage: Optional[Usage] = None
    # Jina specific fields might appear here
    search_summary: Optional[Dict[str, Any]] = Field(None, description="Summary information about the search process.")
