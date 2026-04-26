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


class MemoryListItem(MemoryResponse):
    """Memory record as exposed by GET /v1/memories — includes hierarchy + access count."""
    workspace_id: Optional[str] = None
    app_id: Optional[str] = None
    org_id: Optional[str] = None
    access_count: int = 0


class MemoryListResponse(BaseModel):
    items: list[MemoryListItem]
    total: int
    limit: int
    offset: int


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


class KnowledgeListItem(BaseModel):
    kb_id: str
    name: str
    description: str = ""
    user_id: str
    agent_id: Optional[str] = None
    workspace_id: Optional[str] = None
    app_id: Optional[str] = None
    chunk_count: int = 0
    created_at: float = 0.0


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeListItem]
    total: int
    limit: int
    offset: int


class StatsResponse(BaseModel):
    """Per-user stats from MemWire.get_stats()."""
    memories: int
    nodes: int
    edges: int
    anchors: list[str]
    knowledge_bases: int


class DashboardStatsResponse(BaseModel):
    """Org-wide stats for the Studio dashboard."""
    total_memories: int
    distinct_users: int
    total_nodes: int
    total_edges: int
    total_knowledge_bases: int
    total_anchors: int
    by_category: dict[str, int]
    by_role: dict[str, int]
    timeseries: list[dict]


class ActivityItem(BaseModel):
    type: str
    timestamp: float
    user_id: str
    summary: str
    related_id: str
    role: Optional[str] = None
    category: Optional[str] = None


class ActivityResponse(BaseModel):
    items: list[ActivityItem]


class WorkspaceItem(BaseModel):
    """A workspace_id observed in the data, with aggregate stats."""
    workspace_id: Optional[str] = None
    memory_count: int
    user_count: int
    last_active: float


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceItem]


class HealthResponse(BaseModel):
    status: str
    version: str


# ─── Chat ─────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    user_id: str
    messages: list[ChatMessage]
    model: Optional[str] = None
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    message: ChatMessage
    model: str
    recall: RecallResponse
    usage: Optional[ChatUsage] = None
    recall_ms: float = 0.0
    llm_ms: float = 0.0


class ProviderInfo(BaseModel):
    configured: bool
    base_url: str
    default_model: str
    available_models: list[str]


class ProvidersResponse(BaseModel):
    providers: dict[str, ProviderInfo]


# ─── Graph viz ───────────────────────────────────────────────

class GraphNodeOut(BaseModel):
    node_id: str
    token: str
    memory_ids: list[str]
    connections: int


class GraphEdgeOut(BaseModel):
    source_id: str
    target_id: str
    weight: float


class GraphResponse(BaseModel):
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    total_nodes: int
    total_edges: int
    truncated: bool


# ─── Auth introspection ──────────────────────────────────────

class AuthInfoResponse(BaseModel):
    configured: bool
    configured_count: int
    current_key_prefix: Optional[str] = None


# ─── LLM provider config (UI-managed) ────────────────────────

class LLMConfigItem(BaseModel):
    """Payload for POST /v1/llm/config."""
    api_key: str
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    available_models: Optional[list[str]] = None


class LLMConfigResponse(BaseModel):
    """State of LLM config — what GET /v1/llm/config returns."""
    configured: bool
    env_locked: bool
    base_url: str
    default_model: str
    available_models: list[str]
    api_key_prefix: Optional[str] = None
    api_key_suffix: Optional[str] = None


class LLMTestRequest(BaseModel):
    """Probe payload — if all fields are omitted the current config is tested."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None


class LLMTestResponse(BaseModel):
    ok: bool
    model: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
