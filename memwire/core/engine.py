"""Memory engine — the main orchestrator of core components."""

import time
import uuid

from ..config import MemWireConfig
from ..utils.types import MemoryRecord, TokenEmbedding
from .embeddings import EmbeddingEngine
from .graph import DisplacementGraph
from .classifier import AnchorClassifier


class MemoryEngine:
    """Orchestrates embedding, graph building, and classification."""

    def __init__(self, config: MemWireConfig, qdrant_store=None):
        self.config = config
        self.embeddings = EmbeddingEngine(config)
        self.graph = DisplacementGraph(config, qdrant_store=qdrant_store)
        self.classifier = AnchorClassifier(config)

        # Initialize classifier with embedding function
        self.classifier.initialize(self.embeddings.embed_sentence)

        # Memory storage (in-memory index, backed by DB)
        self._memories: dict[str, MemoryRecord] = {}
        # Map memory_id -> node_ids for cross-linking
        self._memory_nodes: dict[str, list[str]] = {}

    def add_memory(
        self,
        content: str,
        role: str = "user",
        user_id: str = "default",
        agent_id: str | None = None,
        org_id: str = "",
        app_id: str | None = None,
        workspace_id: str | None = None,
    ) -> MemoryRecord:
        """Process and store a new memory. Returns the MemoryRecord."""
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"

        # Embed content directly
        sentence_embedding = self.embeddings.embed_sentence(content)

        # Classify
        category, confidence = self.classifier.classify(sentence_embedding)

        # Get token-level embeddings and build graph
        token_embeddings = self.embeddings.embed_tokens(content)
        node_ids = self.graph.build_from_tokens(
            token_embeddings, memory_id,
            user_id=user_id, app_id=app_id, workspace_id=workspace_id,
        )

        # Cross-link with recent memories only (avoid O(M*T^2) for large histories)
        recent_keys = list(self._memory_nodes.keys())[-self.config.cross_memory_recent_limit:]
        for existing_id in recent_keys:
            if existing_id != memory_id:
                self.graph.merge_cross_memory_edges(node_ids, self._memory_nodes[existing_id])

        # Create memory record
        record = MemoryRecord(
            memory_id=memory_id,
            user_id=user_id,
            content=content,
            role=role,
            embedding=sentence_embedding,
            category=category,
            strength=1.0,
            timestamp=time.time(),
            node_ids=node_ids,
            agent_id=agent_id,
            org_id=org_id,
            workspace_id=workspace_id,
            app_id=app_id,
        )

        self._memories[memory_id] = record
        self._memory_nodes[memory_id] = node_ids
        return record

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        """Retrieve a memory by ID."""
        return self._memories.get(memory_id)

    def get_all_memories(self) -> list[MemoryRecord]:
        """Return all stored memories."""
        return list(self._memories.values())

    def strengthen(self, memory_id: str, amount: float) -> None:
        """Strengthen a memory and its graph edges."""
        record = self._memories.get(memory_id)
        if not record:
            return
        record.strength = min(record.strength + amount, self.config.edge_weight_max)
        # Strengthen edges between this memory's nodes
        nodes = self._memory_nodes.get(memory_id, [])
        for i, nid_a in enumerate(nodes):
            for nid_b in nodes[i + 1:]:
                self.graph.strengthen_edge(nid_a, nid_b, amount)

    def weaken(self, memory_id: str, amount: float) -> None:
        """Weaken a memory and its graph edges."""
        record = self._memories.get(memory_id)
        if not record:
            return
        record.strength = max(record.strength - amount, 0.0)
        nodes = self._memory_nodes.get(memory_id, [])
        for i, nid_a in enumerate(nodes):
            for nid_b in nodes[i + 1:]:
                self.graph.weaken_edge(nid_a, nid_b, amount)

    def decay_all(self) -> int:
        """Apply decay to all graph edges. Returns count of removed edges."""
        return self.graph.decay_all()

    def load_memory(self, record: MemoryRecord) -> None:
        """Load a pre-existing memory record (e.g., from database)."""
        self._memories[record.memory_id] = record
        self._memory_nodes[record.memory_id] = record.node_ids
