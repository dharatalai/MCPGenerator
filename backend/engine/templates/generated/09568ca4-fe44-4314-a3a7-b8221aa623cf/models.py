from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field

# --- Input Models ---

class ChatMessageContentPartText(BaseModel):
    type: Literal["text"]
    text: str

class ChatMessageContentPartImage(BaseModel):
    type: Literal["image_url"]
    image_url: Dict[str, str] # e.g. {"url": "data:image/jpeg;base64,..."}

class ChatMessageContentPartDocument(BaseModel):
    type: Literal["document_url"]
    document_url: Dict[str, str] # e.g. {"url": "data:application/pdf;base64,..."}

ChatMessageContent = Union[
    str, # Simple text content
    List[Union[ # List for multimodal content
        ChatMessageContentPartText,
        ChatMessageContentPartImage,
        ChatMessageContentPartDocument
    ]]
]

class ChatMessage(BaseModel):
    """Represents a single message in the chat conversation."""
    role: Literal['user', 'assistant', 'system'] = Field(..., description="The role of the message author.")
    content: ChatMessageContent = Field(..., description="The content of the message. Can be a simple string for text, or a list of content blocks for multi-modal input (e.g., text + image/document). Image/document content should be provided as data URIs.")
    name: Optional[str] = Field(None, description="An optional name for the participant.")

class DeepSearchChatInput(BaseModel):
    """Input model for the DeepSearch chat completion tool."""
    messages: List[ChatMessage] = Field(..., description="A list of messages comprising the conversation history. Include user queries and any previous assistant responses. Supports text, image, and document content.")
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use. Currently only 'jina-deepsearch-v1' is supported.")
    stream: Optional[bool] = Field(True, description="Whether to stream the response. Strongly recommended to be true to avoid timeouts. The MCP tool will handle stream aggregation internally and return the final result.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains reasoning effort. Supported values: 'low', 'medium', 'high'. Lower effort may yield faster responses with fewer reasoning tokens.")
    budget_tokens: Optional[int] = Field(None, description="Maximum tokens allowed for the DeepSearch process. Overrides 'reasoning_effort'. Larger budgets may improve quality for complex queries.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem. Overrides 'reasoning_effort'. Allows trying different reasoning approaches.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces thinking/search steps even for seemingly trivial queries.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk, sorted by relevance.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="A JSON schema to ensure the final answer conforms to the specified structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        use_enum_values = True # Ensure Literal values are used correctly

# --- Output Models ---

class ResponseMessage(BaseModel):
    """Represents the message generated by the model in the response."""
    role: Literal['assistant'] = Field(..., description="The role of the message author, typically 'assistant'.")
    content: Optional[str] = Field(None, description="The content of the message generated by the model.")

class ResponseChoice(BaseModel):
    """Represents a single choice in the chat completion response."""
    index: int = Field(..., description="The index of the choice in the list of choices.")
    message: ResponseMessage = Field(..., description="The message generated by the model.")
    finish_reason: Optional[str] = Field(None, description="The reason the model stopped generating tokens (e.g., 'stop', 'length').")

class UsageStats(BaseModel):
    """Usage statistics for the completion request."""
    prompt_tokens: Optional[int] = Field(None, description="Number of tokens in the prompt.")
    completion_tokens: Optional[int] = Field(None, description="Number of tokens in the generated completion.")
    total_tokens: Optional[int] = Field(None, description="Total number of tokens used in the request (prompt + completion).")

class DeepSearchChatResponse(BaseModel):
    """Represents the final aggregated response from a DeepSearch chat completion request."""
    id: str = Field(..., description="A unique identifier for the chat completion.")
    object: str = Field(..., description="The object type, typically 'chat.completion'.")
    created: int = Field(..., description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str = Field(..., description="The model used for the chat completion.")
    system_fingerprint: Optional[str] = Field(None, description="This fingerprint represents the backend configuration that the model runs with.")
    choices: List[ResponseChoice] = Field(..., description="A list of chat completion choices. DeepSearch typically returns one choice.")
    usage: Optional[UsageStats] = Field(None, description="Usage statistics for the completion request.")
    # DeepSearch specific fields
    visitedURLs: Optional[List[str]] = Field(None, description="List of all URLs visited during the search process.")
    readURLs: Optional[List[str]] = Field(None, description="List of URLs whose content was read and used for generating the answer.")
    numURLs: Optional[int] = Field(None, description="Total number of unique URLs encountered.")

# --- Stream Chunk Models (for internal aggregation) ---

class StreamDelta(BaseModel):
    role: Optional[Literal['assistant']] = None
    content: Optional[str] = None

class StreamChoice(BaseModel):
    index: int
    delta: StreamDelta
    finish_reason: Optional[str] = None

class StreamChunk(BaseModel):
    id: str
    object: str # e.g., 'chat.completion.chunk'
    created: int
    model: str
    system_fingerprint: Optional[str] = None
    choices: List[StreamChoice]
    # DeepSearch specific fields might appear in the *last* chunk or a separate event
    usage: Optional[UsageStats] = None
    visitedURLs: Optional[List[str]] = None
    readURLs: Optional[List[str]] = None
    numURLs: Optional[int] = None
