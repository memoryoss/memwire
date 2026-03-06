"""Shared type definitions for Vector Pipeline."""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class TokenEmbedding:
    """A single token with its isolated and contextual embeddings."""
    token: str
    position: int
    isolated: np.ndarray          # embedding of token alone
    contextual: np.ndarray        # embedding of token in sentence context
    displacement: np.ndarray      # contextual - isolated

    @property
    def displacement_magnitude(self) -> float:
        return float(np.linalg.norm(self.displacement))


@dataclass
class GraphNode:
    """A node in the displacement graph."""
    node_id: str
    token: str
    embedding: np.ndarray
    memory_ids: list[str] = field(default_factory=list)
    user_id: str = ""
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None

    def __hash__(self):
        return hash(self.node_id)


@dataclass
class GraphEdge:
    """A weighted edge between two graph nodes."""
    source_id: str
    target_id: str
    weight: float = 0.5
    displacement_sim: float = 0.0
    user_id: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.source_id, self.target_id)


@dataclass
class MemoryRecord:
    """A stored memory with its metadata."""
    memory_id: str
    user_id: str
    content: str
    role: str
    embedding: np.ndarray
    category: Optional[str] = None
    strength: float = 1.0
    timestamp: float = 0.0
    node_ids: list[str] = field(default_factory=list)
    agent_id: Optional[str] = None
    access_count: int = 0
    org_id: str = ""
    workspace_id: Optional[str] = None
    app_id: Optional[str] = None


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge from a document."""
    chunk_id: str
    kb_id: str
    user_id: str
    agent_id: Optional[str] = None
    content: str = ""
    metadata: dict = field(default_factory=dict)  # source, page, etc.
    score: float = 0.0  # populated during search
    workspace_id: Optional[str] = None
    app_id: Optional[str] = None


@dataclass
class RecallPath:
    """A path through the graph representing a chain of related memories."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    score: float = 0.0
    memories: list[MemoryRecord] = field(default_factory=list)

    @property
    def total_weight(self) -> float:
        if not self.edges:
            return 0.0
        return sum(e.weight for e in self.edges) / len(self.edges)


@dataclass
class RecallResult:
    """Complete result from a recall operation."""
    query: str
    supporting: list[RecallPath] = field(default_factory=list)
    conflicting: list[RecallPath] = field(default_factory=list)
    knowledge: list[KnowledgeChunk] = field(default_factory=list)
    formatted: str = ""

    @property
    def has_tensions(self) -> bool:
        return len(self.conflicting) > 0

    @property
    def all_paths(self) -> list[RecallPath]:
        return self.supporting + self.conflicting
