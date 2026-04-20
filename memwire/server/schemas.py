"""Pydantic request/response models for the REST API."""

from pydantic import BaseModel, Field
from typing import Optional


# --- Request models ---

class MessageItem(BaseModel):
    role: str
    content: str


class AddMemoryRequest(BaseModel):
    user_id: str
    messages: list[MessageItem]
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


class RecallRequest(BaseModel):
    query: str
    user_id: str
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    user_id: str
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)


class FeedbackRequest(BaseModel):
    assistant_response: str
    user_id: str
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


class AddCategoryRequest(BaseModel):
    name: str
    text: str
    user_id: str
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


class KnowledgeChunkItem(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)


class AddKnowledgeRequest(BaseModel):
    name: str
    chunks: list[KnowledgeChunkItem]
    user_id: str
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


class SearchKnowledgeRequest(BaseModel):
    query: str
    user_id: str
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=100)


class StatsRequest(BaseModel):
    user_id: str
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


# --- Response models ---

class MemoryResponse(BaseModel):
    memory_id: str
    user_id: str
    content: str
    role: str
    category: Optional[str] = None
    strength: float = 1.0
    timestamp: float = 0.0
    node_ids: list[str] = []
    agent_id: Optional[str] = None


class PathResponse(BaseModel):
    tokens: list[str]
    score: float
    memories: list[MemoryResponse]


class RecallResponse(BaseModel):
    query: str
    supporting: list[PathResponse]
    conflicting: list[PathResponse]
    knowledge: list[dict]
    formatted: str
    has_conflicts: bool


class SearchHitResponse(BaseModel):
    memory: MemoryResponse
    score: float


class FeedbackResponse(BaseModel):
    strengthened: int
    weakened: int


class KnowledgeResponse(BaseModel):
    kb_id: str


class IngestResponse(BaseModel):
    kb_id: str
    name: str
    chunks: int


class StatsResponse(BaseModel):
    memories: int
    nodes: int
    edges: int
    anchors: list[str]
    knowledge_bases: int


class HealthResponse(BaseModel):
    status: str
    version: str
