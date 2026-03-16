"""MemWire Python SDK — client for the MemWire REST API."""

__version__ = "0.3.0"

from .client import MemWireClient
from .types import MemoryRecord, RecallResult, RecallPath, KnowledgeChunk, SearchResult

__all__ = [
    "MemWireClient",
    "MemoryRecord",
    "RecallResult",
    "RecallPath",
    "KnowledgeChunk",
    "SearchResult",
]
