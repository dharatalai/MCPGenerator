from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal

# --- Type Definitions from Plan ---

class MessageContentPart(BaseModel):
    type: Literal["text", "image_url"]
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None # e.g., {"url": "data:image/jpeg;base64,..."}

class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal["user", "assistant", "system"] # Added system for completeness, though API might only use user/assistant
    content: Union[str, List[MessageContentPart]] = Field(..., description="The content of the message. Can be a plain string or a list for multimodal inputs.")

class UrlCitation(BaseModel):
    """Details about a URL citation used in the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source.")
    url: Optional[str] = Field(None, description="URL of the source.")
    dateTime: Optional[str] = Field(None, description="Timestamp associated with the citation.")

class Annotation(BaseModel):
    """Annotation within the message content, like a URL citation."""
    type: str = Field(..., description="Type of annotation (e.g., 'url_citation').")
    url_citation: Optional[UrlCitation] = Field(None, description="Details if the annotation is a URL citation.")

class Delta(BaseModel):
    """The delta content for a streaming chunk."""
    role: Optional[Literal["assistant"]] = Field(None, description="Role of the author ('assistant').")
    content: Optional[str] = Field(None, description="The content delta.")
    type: Optional[str] = Field(None, description="Type of content (e.g., 'text').") # Note: API might not send this 'type' field in delta
    annotations: Optional[List[Annotation]] = Field(None, description="Annotations associated with the content delta.")

class Choice(BaseModel):
    """A choice in the chat completion response."""
    index: int = Field(..., description="Index of the choice.")
    delta: Optional[Delta] = Field(None, description="Content delta for streaming response.")
    message: Optional[Message] = Field(None, description="The full message object for non-streaming response.")
    logprobs: Optional[Any] = Field(None, description="Log probability information (typically null).")
    finish_reason: Optional[str] = Field(None, description="Reason the model stopped generating tokens (e.g., 'stop').")

class Usage(BaseModel):
    """Token usage statistics for the request."""
    prompt_tokens: Optional[int] = Field(None, description="Tokens used by the prompt and reasoning process.")
    # Note: DeepSearch API might only return prompt_tokens in usage
    completion_tokens: Optional[int] = Field(None, description="Tokens generated for the completion.")
    total_tokens: Optional[int] = Field(None, description="Total tokens used.")

# --- Input Model for the Tool ---

class DeepSearchChatParams(BaseModel):
    """Input parameters for the DeepSearch chat_completion tool."""
    messages: List[Message] = Field(..., description="A list of messages comprising the conversation history.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use. Currently only 'jina-deepsearch-v1' is supported.")
    stream: Optional[bool] = Field(True, description="Whether to stream back partial progress. Recommended to keep enabled to avoid timeouts.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains effort on reasoning. Supported values: 'low', 'medium', 'high'. Default is 'medium'.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Overrides 'reasoning_effort'.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Overrides 'reasoning_effort'.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces the model to take further thinking/search steps even for seemingly trivial queries. Default is false.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="JSON schema to ensure the final answer matches the supplied structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        # Ensure default values are used correctly
        use_enum_values = True

# --- Response Models (Mimicking OpenAI Schema) ---

class ChatCompletionResponse(BaseModel):
    """Response model for non-streaming chat completion, compatible with OpenAI schema."""
    id: str = Field(..., description="A unique identifier for the chat completion.")
    object: str = Field("chat.completion", description="The object type, which is always 'chat.completion'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str = Field(..., description="The model used for the chat completion.")
    choices: List[Choice] = Field(..., description="A list of chat completion choices. Can be more than one if n > 1 was requested.")
    usage: Optional[Usage] = Field(None, description="Usage statistics for the completion request.")
    # DeepSearch specific fields
    visitedURLs: Optional[List[str]] = Field(None, description="URLs visited during the search process.")
    readURLs: Optional[List[str]] = Field(None, description="URLs read and used for reasoning.")
    numURLs: Optional[int] = Field(None, description="Number of URLs read.")

class ChatCompletionChunk(BaseModel):
    """Response model for streaming chat completion chunks, compatible with OpenAI schema."""
    id: str = Field(..., description="A unique identifier for the chat completion. Each chunk has the same ID.")
    object: str = Field("chat.completion.chunk", description="The object type, which is always 'chat.completion.chunk'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str = Field(..., description="The model used for the chat completion.")
    choices: List[Choice] = Field(..., description="A list of chat completion choices. For streaming, this usually contains one choice with a delta.")
    usage: Optional[Usage] = Field(None, description="Usage statistics for the completion request. Only appears in the final chunk.")
    # DeepSearch specific fields (might appear in chunks, especially final one)
    visitedURLs: Optional[List[str]] = Field(None)
    readURLs: Optional[List[str]] = Field(None)
    numURLs: Optional[int] = Field(None)
