from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal

# Type Definitions based on Implementation Plan

class ChatMessageContentPart(BaseModel):
    """Represents a part of the content in a message, can be text, image URL, or document URL."""
    type: Literal['text', 'image_url', 'document_url'] = Field(..., description="The type of the content part.")
    text: Optional[str] = Field(None, description="The text content.")
    image_url: Optional[Dict[str, str]] = Field(None, description="The image URL object, expecting {'url': 'data:image/...'}.")
    document_url: Optional[Dict[str, str]] = Field(None, description="The document URL object, expecting {'url': 'data:application/pdf...' or 'data:text/plain...'}.")

class ChatMessage(BaseModel):
    """Represents a single message in the conversation."""
    role: Literal['user', 'assistant'] = Field(..., description="The role of the message author.")
    content: Union[str, List[ChatMessageContentPart]] = Field(..., description="The content of the message. Can be simple text or a list of content parts for multimodal input.")

class UrlCitation(BaseModel):
    """Details of a URL citation used in the response."""
    title: Optional[str] = Field(None, description="Title of the cited web page.")
    exactQuote: Optional[str] = Field(None, description="The exact quote from the source.")
    url: Optional[str] = Field(None, description="URL of the source.")

class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: Optional[int] = Field(None, description="Number of tokens in the prompt.")
    completion_tokens: Optional[int] = Field(None, description="Number of tokens in the completion.")
    total_tokens: Optional[int] = Field(None, description="Total number of tokens used.")

# Input Model for the chat_completion tool

class DeepSearchChatInput(BaseModel):
    """Input model for the DeepSearch chat completion tool."""
    messages: List[ChatMessage] = Field(..., description="A list of messages comprising the conversation history. Can include user, assistant roles. Content can include text, or data URIs for images (webp, png, jpeg) or documents (txt, pdf) up to 10MB.")
    model: str = Field("jina-deepsearch-v1", description="ID of the DeepSearch model to use.")
    stream: bool = Field(True, description="Whether to stream back partial progress using server-sent events. Recommended to keep true to avoid timeouts on long requests.")
    reasoning_effort: Optional[Literal['low', 'medium', 'high']] = Field("medium", description="Constrains effort on reasoning. 'low', 'medium', or 'high'. Lower effort may be faster but less thorough. Overridden by 'budget_tokens' or 'max_attempts'.")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the DeepSearch process. Larger budgets can improve quality for complex queries. Overrides 'reasoning_effort'.")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem using different approaches. Overrides 'reasoning_effort'.")
    no_direct_answer: Optional[bool] = Field(False, description="Forces thinking/search steps even if the query seems trivial.")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer/chunk, sorted by relevance.")
    structured_output: Optional[Dict[str, Any]] = Field(None, description="A JSON schema to ensure the final answer matches the specified structure.")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize for content retrieval.")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to strictly exclude from content retrieval.")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include in content retrieval.")

    class Config:
        use_enum_values = True # Ensure Literal values are handled correctly

# Response Models (Streaming and Non-Streaming)

class ChoiceDelta(BaseModel):
    """Content delta within a streaming chunk."""
    role: Optional[Literal['assistant']] = Field(None)
    content: Optional[str] = Field(None)

class Choice(BaseModel):
    """A single choice in a non-streaming response."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None
    citations: Optional[List[UrlCitation]] = Field(None, description="List of citations used for the response.")

class DeepSearchChatChunk(BaseModel):
    """Represents a chunk of data in a streaming response."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]] # Raw choices data, might contain delta or full message parts
    usage: Optional[Usage] = Field(None, description="Usage statistics, typically provided in the final chunk.")
    citations: Optional[List[UrlCitation]] = Field(None, description="List of citations, potentially updated across chunks.")
    # The actual structure of 'choices' in chunks can vary. Often it's like:
    # choices: List[{"index": int, "delta": ChoiceDelta, "finish_reason": Optional[str]}]
    # We keep it flexible with Dict[str, Any] for broader compatibility.

class DeepSearchChatResponse(BaseModel):
    """Represents the full response for a non-streaming request."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    citations: Optional[List[UrlCitation]] = Field(None, description="List of citations used for the response.")
