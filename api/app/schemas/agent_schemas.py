from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: Optional[str] = Field(
        None, description="System prompt injected before context"
    )
    history_turns: int = Field(20, ge=1, le=100)
    max_context_tokens: int = Field(2000, ge=100, le=8000)
    knowledge_enabled: bool = True
    knowledge_results: int = Field(5, ge=1, le=20)


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    history_turns: Optional[int] = Field(None, ge=1, le=100)
    max_context_tokens: Optional[int] = Field(None, ge=100, le=8000)
    knowledge_enabled: Optional[bool] = None
    knowledge_results: Optional[int] = Field(None, ge=1, le=20)


class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    history_turns: int
    max_context_tokens: int
    knowledge_enabled: bool
    knowledge_results: int
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


class DeleteAgentResponse(BaseModel):
    success: bool
    agent_id: str
    message: str


# ── API Key schemas ───────────────────────────────────────────


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    key_prefix: str  # First 8 chars, e.g. "mw_abc12..."
    created_at: datetime
    last_used_at: Optional[datetime]


class CreateAPIKeyResponse(BaseModel):
    id: str
    name: str
    key: str  # Full key — shown only on creation
    key_prefix: str
    created_at: datetime
    message: str = "Store this key securely. It will not be shown again."


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyResponse]
    total: int


class DeleteAPIKeyResponse(BaseModel):
    success: bool
    key_id: str
