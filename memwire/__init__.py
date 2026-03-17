"""MemWire — pure vector-based memory infrastructure for AI agents.

No LLM calls for classification, entity detection, or recall.
Displacement-based graph construction from token embeddings,
path-based recall with tension detection, and explicit API.

Usage:
    from memwire import MemWire, MemWireConfig

    config = MemWireConfig(org_id="my_org")
    memory = MemWire(config=config)
    memory.add(user_id="buyer_1", messages=[{"role": "user", "content": "We prefer organic materials"}])
    result = memory.recall("Which vendor should we use?", user_id="buyer_1")
    memory.feedback(assistant_response="Based on your preference for organic, I recommend Vendor A", user_id="buyer_1")
"""

__version__ = "0.1.0"

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
