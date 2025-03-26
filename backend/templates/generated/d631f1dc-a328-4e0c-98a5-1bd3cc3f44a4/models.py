from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class Message(BaseModel):
    """
    A message in the conversation history for DeepSearch.
    """
    role: str = Field(..., description="The role of the message ('user' or 'assistant')")
    content: str = Field(..., description="The content of the message")

class ReasoningEffort(str, Enum):
    """
    The effort level for reasoning in DeepSearch queries.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DeepSearchQueryParams(BaseModel):
    """
    Parameters for querying the DeepSearch API.
    """
    model: str = Field(
        "jina-deepsearch-v1",
        description="The model to use for the query. Currently supports 'jina-deepsearch-v1'."
    )
    messages: List[Message] = Field(
        ...,
        description="A list of messages representing the conversation history."
    )
    stream: bool = Field(
        True,
        description="Whether to enable streaming of intermediate results. Recommended to keep enabled."
    )
    reasoning_effort: ReasoningEffort = Field(
        ReasoningEffort.MEDIUM,
        description="The effort level for reasoning. Possible values: 'low', 'medium', 'high'."
    )
    budget_tokens: Optional[int] = Field(
        None,
        description="The maximum number of tokens allowed for the process."
    )
    max_attempts: Optional[int] = Field(
        None,
        description="The maximum number of retries for solving the problem."
    )
    no_direct_answer: bool = Field(
        False,
        description="Forces the model to take further thinking/search steps even when the query seems trivial."
    )
    max_returned_urls: Optional[int] = Field(
        None,
        description="The maximum number of URLs to include in the final answer."
    )
    structured_output: bool = Field(
        False,
        description="Enables Structured Outputs based on a supplied JSON schema."
    )
    good_domains: Optional[List[str]] = Field(
        None,
        description="Domains to prioritize for content retrieval."
    )
    bad_domains: Optional[List[str]] = Field(
        None,
        description="Domains to exclude from content retrieval."
    )
    only_domains: Optional[List[str]] = Field(
        None,
        description="Domains to exclusively include in content retrieval."
    )

class DeepSearchResponse(BaseModel):
    """
    Response model from DeepSearch API.
    """
    answer: str = Field(..., description="The generated answer from DeepSearch")
    visited_urls: List[Dict[str, Any]] = Field(
        [],
        description="List of URLs visited during the search process"
    )
    usage: Dict[str, int] = Field(
        ...,
        description="Token usage information including prompt and completion tokens"
    )
    structured_output: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured output if requested"
    )