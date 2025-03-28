from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal

# --- Type Definitions from Plan ---

class UrlCitation(BaseModel):
    """Details of a URL citation used in the response."""
    title: str = Field(..., description="Title of the cited web page.")
    exactQuote: str = Field(..., description="The exact quote from the source.")
    url: str = Field(..., description="URL of the source.")
    dateTime: str = Field(..., description="Timestamp of when the content was accessed or published.")

class UrlCitationAnnotation(BaseModel):
    """Annotation indicating a URL citation."""
    type: str = Field(..., description="Type of annotation, e.g., 'url_citation'.")
    url_citation: UrlCitation = Field(..., description="Details of the citation.")

class Delta(BaseModel):
    """The change in content for a streaming chunk."""
    content: Optional[str] = Field(None, description="The text content delta.")
    type: Optional[str] = Field(None, description="Type of content, e.g., 'text'.")
    annotations: Optional[List[UrlCitationAnnotation]] = Field(None, description="List of annotations for the content delta.")

class MessageContentItem(BaseModel):
    """Represents a part of the message content, which can be text, an image, or a document."""
    type: Literal['text', 'image_url', 'document_url'] = Field(..., description="Type of content ('text', 'image_url', 'document_url')")
    text: Optional[str] = Field(None, description="Text content. Required if type is 'text'.")
    image_url: Optional[Dict[str, str]] = Field(None, description="Dictionary containing 'url' key with data URI for image (webp, png, jpeg). Required if type is 'image_url'.")
    document_url: Optional[Dict[str, str]] = Field(None, description="Dictionary containing 'url' key with data URI for document (txt, pdf). Required if type is 'document_url'.")

    model_config = {
        "extra": "forbid"
    }

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant'] = Field(..., description="Role of the message sender ('user' or 'assistant').")
    content: Union[str, List[MessageContentItem]] = Field(..., description="Content of the message. Can be a simple string or a list of content items for multimodal input.")

    model_config = {
        "extra": "forbid"
    }

# --- Input Model for chat_completion Tool ---

class DeepSearchChatInput(BaseModel):
    """Input model for the Jina DeepSearch chat completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use. Currently only 'jina-deepsearch-v1' is supported.")
    stream: Optional[bool] = Field(True, description="Whether to stream back partial progress. Strongly recommended (default: true).")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains effort on reasoning. Default: 'medium'.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed. Overrides 'reasoning_effort'.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries. Overrides 'reasoning_effort'.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces search/thinking steps even for trivial queries. Default: false.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="A JSON schema to ensure the final answer conforms to the specified structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include.")

    model_config = {
        "extra": "forbid" # Forbid extra fields not defined in the model
    }

# --- Potentially useful for parsing responses, though tool returns Dict[str, Any] ---

class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class DeepSearchChatResponse(BaseModel):
    """Represents the structure of a non-streaming response (for reference)."""
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage
    # Potentially other fields like citations, visited_urls etc.
    # The actual response structure might vary, hence the tool returns Dict[str, Any].
