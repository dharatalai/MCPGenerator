from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal

# --- Type Definitions from Plan ---

class MessageContentPartText(BaseModel):
    """Represents a text part of a message content."""
    type: Literal['text'] = Field(..., description="The type of the content part.")
    text: str = Field(..., description="The text content.")

class MessageContentPartImageURLData(BaseModel):
    """Structure for the image URL data."""
    url: str = Field(..., description="The URL of the image, typically a data URI.")

class MessageContentPartImageURL(BaseModel):
    """Represents an image URL part of a message content."""
    type: Literal['image_url'] = Field(..., description="The type of the content part.")
    image_url: MessageContentPartImageURLData = Field(..., description="A dictionary containing the URL.")

class MessageContentPartDocumentURLData(BaseModel):
    """Structure for the document URL data."""
    url: str = Field(..., description="The URL of the document, typically a data URI.")

class MessageContentPartDocumentURL(BaseModel):
    """Represents a document URL part of a message content."""
    type: Literal['document_url'] = Field(..., description="The type of the content part.")
    document_url: MessageContentPartDocumentURLData = Field(..., description="A dictionary containing the URL.")

MessageContentPart = Union[MessageContentPartText, MessageContentPartImageURL, MessageContentPartDocumentURL]

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant', 'system'] = Field(..., description="The role of the message author.")
    content: Union[str, List[MessageContentPart]] = Field(..., description="The content of the message.")

class UrlCitation(BaseModel):
    """Details about a URL citation used in the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source.")
    url: str = Field(..., description="The URL of the source.")
    dateTime: Optional[str] = Field(None, description="Timestamp associated with the citation.")

class Annotation(BaseModel):
    """Annotation within the response content."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitation] = Field(None, description="Details if the annotation is a URL citation.")

class ChoiceDelta(BaseModel):
    """The delta update for a choice in a streaming response."""
    content: Optional[str] = Field(None, description="The content delta.")
    role: Optional[Literal['assistant']] = Field(None, description="Role of the author of the message delta.") # Added based on typical OpenAI schema
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').")
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations associated with this delta.")

class ChatCompletionChunkChoice(BaseModel):
    """A choice within a streaming chat completion chunk."""
    index: int = Field(..., description="The index of the choice.")
    delta: ChoiceDelta = Field(..., description="The delta change for this choice.")
    finish_reason: Optional[str] = Field(None, description="Reason the model stopped generating tokens.") # Added based on typical OpenAI schema
    logprobs: Optional[Any] = Field(None, description="Log probability information, if requested.")

class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: Optional[int] = Field(None, description="Number of tokens in the prompt.")
    completion_tokens: Optional[int] = Field(None, description="Number of tokens in the generated completion.")
    total_tokens: Optional[int] = Field(None, description="Total number of tokens used in the request.")
    search_requests: Optional[int] = Field(None, description="Number of search requests performed.")
    search_requests_used: Optional[int] = Field(None, description="Number of search requests actually used.")

# --- Input Model --- 

class DeepSearchChatInput(BaseModel):
    """Input model for the Jina DeepSearch chat completions tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use.")
    stream: bool = Field(True, description="Whether to stream back partial progress and the final answer.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains reasoning effort ('low', 'medium', 'high').")
    budget_tokens: Optional[int] = Field(None, description="Maximum tokens allowed for the DeepSearch process.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces further thinking/search steps.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="JSON schema to ensure the final answer matches the structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

# --- Output Models (Based on OpenAI Schema & DeepSearch additions) ---

class ChatCompletionChoice(BaseModel):
    """A choice in a non-streaming chat completion response."""
    index: int = Field(..., description="The index of the choice.")
    message: Message = Field(..., description="The message generated by the model.")
    finish_reason: Optional[str] = Field(None, description="Reason the model stopped generating tokens.")
    logprobs: Optional[Any] = Field(None, description="Log probability information, if requested.")
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations associated with the final message.")

class ChatCompletion(BaseModel):
    """Represents a non-streaming chat completion response."""
    id: str = Field(..., description="A unique identifier for the chat completion.")
    object: str = Field("chat.completion", description="The object type, always 'chat.completion'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str = Field(..., description="The model used for the chat completion.")
    choices: List[ChatCompletionChoice] = Field(..., description="A list of chat completion choices.")
    usage: Optional[Usage] = Field(None, description="Usage statistics for the completion request.")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint for the model.")
    visited_urls: Optional[List[str]] = Field(None, description="List of URLs visited during the search process.") # DeepSearch specific

class ChatCompletionChunk(BaseModel):
    """Represents a streaming chat completion chunk."""
    id: str = Field(..., description="A unique identifier for the chat completion chunk.")
    object: str = Field("chat.completion.chunk", description="The object type, always 'chat.completion.chunk'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chunk was created.")
    model: str = Field(..., description="The model used for the chat completion.")
    choices: List[ChatCompletionChunkChoice] = Field(..., description="A list of chat completion choices.")
    usage: Optional[Usage] = Field(None, description="Usage statistics, present in the final chunk.")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint for the model.")
    visited_urls: Optional[List[str]] = Field(None, description="List of URLs visited, present in the final chunk.") # DeepSearch specific
