"""SDK data types."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MemoryRecord:
    memory_id: str
    user_id: str
    content: str
    role: str
    category: Optional[str] = None
    strength: float = 1.0
    timestamp: float = 0.0
    node_ids: list[str] = field(default_factory=list)
    agent_id: Optional[str] = None


@dataclass
class KnowledgeChunk:
    chunk_id: str
    kb_id: str
    content: str
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class RecallPath:
    tokens: list[str]
    score: float
    memories: list[MemoryRecord] = field(default_factory=list)


@dataclass
class RecallResult:
    query: str
    supporting: list[RecallPath] = field(default_factory=list)
    conflicting: list[RecallPath] = field(default_factory=list)
    knowledge: list[KnowledgeChunk] = field(default_factory=list)
    formatted: str = ""
    has_conflicts: bool = False


@dataclass
class SearchResult:
    memory: MemoryRecord
    score: float
