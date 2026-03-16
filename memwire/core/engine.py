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

        self.classifier.initialize(self.embeddings.embed_sentence)

        self._memories: dict[str, MemoryRecord] = {}
        self._memory_nodes: dict[str, list[str]] = {}  # memory_id -> node_ids

    def add_memory(
        self,
        content: str,
        role: str = "user",
        user_id: str = "default",
        agent_id: str | None = None,
        org_id: str = "",
        app_id: str | None = None,
        workspace_id: str | None = None,
        graph: "DisplacementGraph | None" = None,
        memory_nodes: dict[str, list[str]] | None = None,
    ) -> MemoryRecord:
        """Process and store a new memory. Returns the MemoryRecord."""
        target_graph = graph or self.graph
        target_nodes = memory_nodes if memory_nodes is not None else self._memory_nodes
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"

        sentence_embedding = self.embeddings.embed_sentence(content)
        category, confidence = self.classifier.classify(sentence_embedding)
        token_embeddings = self.embeddings.embed_tokens(content)
        node_ids = target_graph.build_from_tokens(
            token_embeddings, memory_id,
            user_id=user_id, app_id=app_id, workspace_id=workspace_id,
        )

        # cross-link with recent memories only (scoped to the provided dict)
        recent_keys = list(target_nodes.keys())[-self.config.cross_memory_recent_limit:]
        for existing_id in recent_keys:
            if existing_id != memory_id:
                target_graph.merge_cross_memory_edges(node_ids, target_nodes[existing_id])

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
        target_nodes[memory_id] = node_ids
        return record

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        """Retrieve a memory by ID."""
        return self._memories.get(memory_id)

    def get_all_memories(self) -> list[MemoryRecord]:
        """Return all stored memories."""
        return list(self._memories.values())

    def strengthen(self, memory_id: str, amount: float, graph: "DisplacementGraph | None" = None, memory_nodes: dict[str, list[str]] | None = None) -> None:
        """Strengthen a memory and its graph edges."""
        target_graph = graph or self.graph
        target_nodes = memory_nodes if memory_nodes is not None else self._memory_nodes
        record = self._memories.get(memory_id)
        if not record:
            return
        record.strength = min(record.strength + amount, self.config.edge_weight_max)
        nodes = target_nodes.get(memory_id, [])
        for i, nid_a in enumerate(nodes):
            for nid_b in nodes[i + 1:]:
                target_graph.strengthen_edge(nid_a, nid_b, amount)

    def weaken(self, memory_id: str, amount: float, graph: "DisplacementGraph | None" = None, memory_nodes: dict[str, list[str]] | None = None) -> None:
        """Weaken a memory and its graph edges."""
        target_graph = graph or self.graph
        target_nodes = memory_nodes if memory_nodes is not None else self._memory_nodes
        record = self._memories.get(memory_id)
        if not record:
            return
        record.strength = max(record.strength - amount, 0.0)
        nodes = target_nodes.get(memory_id, [])
        for i, nid_a in enumerate(nodes):
            for nid_b in nodes[i + 1:]:
                target_graph.weaken_edge(nid_a, nid_b, amount)

    def decay_all(self, graph: "DisplacementGraph | None" = None) -> int:
        """Apply decay to all graph edges. Returns count of removed edges."""
        target_graph = graph or self.graph
        return target_graph.decay_all()

    def load_memory(self, record: MemoryRecord) -> None:
        """Load a pre-existing memory record (e.g., from database)."""
        self._memories[record.memory_id] = record
        self._memory_nodes[record.memory_id] = record.node_ids
