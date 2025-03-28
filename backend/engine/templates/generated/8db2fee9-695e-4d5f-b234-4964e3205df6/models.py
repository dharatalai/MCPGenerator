from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Union, Literal

# --- Input Models ---

class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str = Field(..., description="The text content.")

class ImageUrl(BaseModel):
    url: str = Field(..., description="Data URI (e.g., 'data:image/jpeg;base64,...') or HTTPS URL of the image.")

class ImageContent(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: ImageUrl = Field(..., description="The image URL object.")

class DocumentUrl(BaseModel):
    url: str = Field(..., description="Data URI (e.g., 'data:application/pdf;base64,...') of the document.")

class DocumentContent(BaseModel):
    type: Literal["document_url"] = "document_url"
    document_url: DocumentUrl = Field(..., description="The document URL object.")

# Use Union for content type flexibility, matching OpenAI's schema
ContentType = Union[TextContent, ImageContent, DocumentContent]

class Message(BaseModel):
    """Represents a single message in the conversation history."""
    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender.")
    content: Union[str, List[ContentType]] = Field(..., description="The content of the message. Can be a simple string or a list of content blocks for multimodal input (text, image, document).")
    name: str | None = Field(None, description="An optional name for the participant.")

class DeepSearchChatInput(BaseModel):
    """Input model for the DeepSearch chat_completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history. Follows OpenAI schema.")
    stream: bool = Field(False, description="Whether to stream the response. If true, intermediate results might be returned. MCP currently handles the final aggregated response.")
    # Add other potential OpenAI compatible parameters if needed, e.g., max_tokens, temperature
    # model: str = Field("jina-deepsearch", description="The model identifier, defaults to Jina DeepSearch.") # Usually set in the client

# --- Output Models ---

class Source(BaseModel):
    """Represents a cited source used to generate the answer."""
    url: HttpUrl = Field(..., description="The URL of the source.")
    title: str | None = Field(None, description="The title of the source page.")
    snippet: str | None = Field(None, description="A relevant snippet from the source.")

class Usage(BaseModel):
    """Token usage statistics for the request."""
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt.")
    completion_tokens: int = Field(..., description="Number of tokens in the generated completion.")
    total_tokens: int = Field(..., description="Total number of tokens used.")

class DeepSearchChatOutput(BaseModel):
    """Output model for the DeepSearch chat_completion tool."""
    answer: str = Field(..., description="The final generated answer from DeepSearch.")
    sources: List[Source] = Field([], description="A list of sources cited in the answer.")
    usage: Usage | None = Field(None, description="Token usage information for the request.")
    # Include other fields from the API response if necessary
    id: str | None = Field(None, description="A unique identifier for the chat completion.")
    object: str | None = Field(None, description="The object type, typically 'chat.completion'.")
    created: int | None = Field(None, description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str | None = Field(None, description="The model used for the chat completion.")
    system_fingerprint: str | None = Field(None, description="This fingerprint represents the backend configuration that the model runs with.")
    finish_reason: str | None = Field(None, description="The reason the model stopped generating tokens.")
