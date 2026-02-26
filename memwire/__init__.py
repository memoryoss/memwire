"""MemWire — pure vector-based memory infrastructure for AI agents.

No LLM calls for classification, entity detection, or recall.
Displacement-based graph construction from token embeddings,
path-based recall with tension detection, and explicit API.

Usage:
    from memwire import MemWire

    memory = MemWire(user_id="buyer_1")
    memory.add([{"role": "user", "content": "We prefer organic materials"}])
    result = memory.recall("Which vendor should we use?")
    memory.feedback(response="Based on your preference for organic, I recommend Vendor A")
"""

__version__ = "0.2.0"

from .api.client import MemWire
from .config import MemWireConfig
from .utils.types import (
    TokenEmbedding,
    GraphNode,
    GraphEdge,
    MemoryRecord,
    RecallPath,
    RecallResult,
    KnowledgeChunk,
)

__all__ = [
    "MemWire",
    "MemWireConfig",
    "TokenEmbedding",
    "GraphNode",
    "GraphEdge",
    "MemoryRecord",
    "RecallPath",
    "RecallResult",
    "KnowledgeChunk",
]
