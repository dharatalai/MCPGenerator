from pydantic import BaseModel, Field
from typing import List, Optional

class Message(BaseModel):
    """Represents a message in the conversation"""
    role: str = Field(..., description="Role of the message (user or assistant)")
    content: str = Field(..., description="Content of the message")

class ResponseChunk(BaseModel):
    """Represents a chunk of the response"""
    content: Optional[str] = Field(None, description="Content of the chunk")
    type: Optional[str] = Field(None, description="Type of the chunk (e.g., text)")

class DeepSearchChatParams(BaseModel):
    """Parameters for DeepSearch chat completions"""
    model: str = Field("jina-deepsearch-v1", description="ID of the model to use")
    messages: List[Message] = Field(..., description="List of messages between the user and the assistant")
    stream: bool = Field(True, description="Whether to enable streaming of results")
    reasoning_effort: str = Field("medium", description="Level of reasoning effort (low, medium, high)")
    budget_tokens: Optional[int] = Field(None, description="Maximum number of tokens allowed for the process")
    max_attempts: Optional[int] = Field(None, description="Maximum number of retries for solving the problem")
    no_direct_answer: bool = Field(False, description="Force the model to take further thinking steps")
    max_returned_urls: Optional[int] = Field(None, description="Maximum number of URLs to include in the final answer")
    structured_output: bool = Field(False, description="Enable Structured Outputs")
    good_domains: Optional[List[str]] = Field(None, description="List of domains to prioritize")
    bad_domains: Optional[List[str]] = Field(None, description="List of domains to exclude")
    only_domains: Optional[List[str]] = Field(None, description="List of domains to exclusively include")