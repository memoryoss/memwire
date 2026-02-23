from pydantic import BaseModel, Field
from typing import Optional


class ContextSnapshotRequest(BaseModel):
    agent_id: str = Field(..., description="Agent identifier")
    user_id: str = Field(..., description="User/customer identifier")
    query: str = Field(..., description="Current user message or query")
    history_turns: int = Field(
        10, ge=1, le=50, description="Number of past turns to include"
    )
    include_knowledge: bool = Field(
        True, description="Whether to include knowledge base results"
    )
    knowledge_results: int = Field(
        5, ge=1, le=20, description="Max knowledge chunks to include"
    )
    max_tokens: Optional[int] = Field(
        None, description="Override max token budget for context"
    )
    session_id: Optional[str] = Field(
        None, description="Restrict history to a specific session"
    )


class ContextSnapshotResponse(BaseModel):
    context: str = Field(
        ...,
        description="Assembled context string, ready to inject into a system prompt",
    )
    memory_hits: int = Field(..., description="Number of conversation turns included")
    knowledge_hits: int = Field(..., description="Number of knowledge chunks included")
    token_estimate: int = Field(
        ..., description="Rough token count estimate of the context string"
    )
    agent_id: str
    user_id: str
