"""MemWire — the explicit user-facing API."""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from ..config import MemWireConfig
from ..core.engine import MemoryEngine
from ..core.recall import RecallEngine
from ..core.feedback import FeedbackProcessor
from ..storage.database import DatabaseManager
from ..storage.qdrant_store import QdrantStore
from ..storage.vector_ops import find_similar_memories, rebuild_graph_from_db
from ..utils.types import RecallResult, MemoryRecord, KnowledgeChunk
from .formatter import MemoryFormatter

logger = logging.getLogger(__name__)


class MemWire:
    """Explicit API for vector-based memory. No automatic LLM interception."""

    def __init__(
        self,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        config: Optional[MemWireConfig] = None,
    ):
        self.config = config or MemWireConfig()
        self.config.user_id = user_id
        self.user_id = user_id
        self.agent_id = agent_id

        # Qdrant store (always required)
        self.qdrant_store = QdrantStore(self.config)

        # Core components
        self.engine = MemoryEngine(self.config, qdrant_store=self.qdrant_store)
        self.recall_engine = RecallEngine(self.config)
        self.feedback_processor = FeedbackProcessor(self.config)
        self.formatter = MemoryFormatter()

        # SQLite storage (metadata ledger — edges, anchors, KB metadata)
        self.db = DatabaseManager(self.config)

        # Reranker (lazy-loaded if enabled)
        self._reranker = None

        # Background processing
        self._executor = ThreadPoolExecutor(max_workers=self.config.background_threads)

        # Last recall result (for feedback)
        self._last_recall: Optional[RecallResult] = None

        # Load persisted state
        self._load_from_db()

    def _get_reranker(self):
        if self._reranker is None:
            from ..core.reranker import Reranker
            self._reranker = Reranker(self.config)
        return self._reranker

    def _submit_bg(self, fn, *args):
        """Submit background task with error logging."""
        future = self._executor.submit(fn, *args)
        future.add_done_callback(self._handle_bg_error)

    @staticmethod
    def _handle_bg_error(future):
        exc = future.exception()
        if exc:
            logger.error("Background persistence error: %s", exc, exc_info=True)

    def add(self, messages: list[dict[str, str]]) -> list[MemoryRecord]:
        """Add memories from message dicts. Each must have 'role' and 'content'."""
        records = []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "user")
            if not content.strip():
                continue
            record = self.engine.add_memory(
                content, role=role, user_id=self.user_id, agent_id=self.agent_id,
            )
            records.append(record)

            # Compute sparse embedding for Qdrant
            sparse_data = None
            try:
                indices, values = self.engine.embeddings.embed_sparse(content)
                sparse_data = (indices, values)
            except Exception as e:
                logger.warning("Sparse embedding failed: %s", e)

            # Persist asynchronously
            self._submit_bg(self._persist_memory, record, sparse_data)
        return records

    def recall(self, query: str) -> RecallResult:
        """Recall relevant memory paths for a query."""
        query_embedding = self.engine.embeddings.embed_sentence(query)

        # Compute sparse embedding for knowledge search
        sparse_indices = None
        sparse_values = None
        try:
            sparse_indices, sparse_values = self.engine.embeddings.embed_sparse(query)
        except Exception as e:
            logger.warning("Sparse embedding failed for recall: %s", e)

        result = self.recall_engine.recall(
            query_embedding=query_embedding,
            graph=self.engine.graph,
            memories=self.engine._memories,
            query_text=query,
            qdrant_store=self.qdrant_store,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            user_id=self.user_id,
            agent_id=self.agent_id,
        )

        result.formatted = self.formatter.format(result)
        self._last_recall = result
        return result

    def feedback(self, response: str) -> dict[str, int]:
        """Provide feedback from LLM response to strengthen/weaken paths."""
        if not self._last_recall:
            return {"strengthened": 0, "weakened": 0}

        response_embedding = self.engine.embeddings.embed_sentence(response)
        stats = self.feedback_processor.process(
            response_embedding, self._last_recall, self.engine.graph
        )

        # Persist only dirty edge changes asynchronously
        self._submit_bg(self._persist_graph)
        return stats

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 10,
    ) -> list[tuple[MemoryRecord, float]]:
        """Search memories by similarity, optionally filtered by category."""
        query_embedding = self.engine.embeddings.embed_sentence(query)

        # Compute sparse embedding for hybrid search
        sparse_indices = None
        sparse_values = None
        try:
            sparse_indices, sparse_values = self.engine.embeddings.embed_sparse(query)
        except Exception as e:
            logger.warning("Sparse embedding failed for search: %s", e)

        results = find_similar_memories(
            query_embedding,
            self.engine.get_all_memories(),
            top_k=top_k * 2 if self.config.use_reranking else top_k,
            category=category,
            qdrant_store=self.qdrant_store,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            user_id=self.user_id,
            agent_id=self.agent_id,
            memory_dict=self.engine._memories,
        )

        # Optional cross-encoder reranking
        if self.config.use_reranking and results:
            reranker = self._get_reranker()
            results = reranker.rerank(query, results, top_k=top_k)

        return results[:top_k]

    def add_anchor(self, name: str, text: str) -> None:
        """Add or update a classification anchor."""
        self.engine.classifier.add_anchor(
            name, text, self.engine.embeddings.embed_sentence
        )
        # Save the full texts list so multi-text anchors survive restart
        texts = self.engine.classifier.get_anchors().get(name, [text])
        self._submit_bg(
            self.db.save_anchor, name, self.user_id, texts
        )

    # --- Knowledge Base API ---

    def add_knowledge(self, name: str, chunks: list[dict]) -> str:
        """Add a knowledge base. Each chunk dict has 'content' and optional 'metadata'.

        Returns kb_id.
        """
        kb_id = f"kb_{uuid.uuid4().hex[:12]}"

        # Save KB metadata to SQLite
        self.db.save_knowledge_base(
            kb_id=kb_id,
            user_id=self.user_id,
            name=name,
            agent_id=self.agent_id,
            chunk_count=len(chunks),
        )

        # Embed and save each chunk to Qdrant
        for i, chunk_data in enumerate(chunks):
            content = chunk_data.get("content", "")
            metadata = chunk_data.get("metadata", {})
            if not content.strip():
                continue

            chunk_id = f"{kb_id}_chunk_{i}"
            dense_emb = self.engine.embeddings.embed_sentence(content)

            sparse_indices = None
            sparse_values = None
            try:
                sparse_indices, sparse_values = self.engine.embeddings.embed_sparse(content)
            except Exception as e:
                logger.warning("Sparse embedding failed for chunk: %s", e)

            self.qdrant_store.save_knowledge_chunk(
                chunk_id=chunk_id,
                dense_embedding=dense_emb,
                kb_id=kb_id,
                user_id=self.user_id,
                content=content,
                agent_id=self.agent_id,
                metadata=metadata,
                sparse_indices=sparse_indices,
                sparse_values=sparse_values,
            )

        return kb_id

    def search_knowledge(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        """Direct search over knowledge chunks."""
        query_embedding = self.engine.embeddings.embed_sentence(query)

        sparse_indices = None
        sparse_values = None
        try:
            sparse_indices, sparse_values = self.engine.embeddings.embed_sparse(query)
        except Exception as e:
            logger.warning("Sparse embedding failed for knowledge search: %s", e)

        return self.recall_engine.search_knowledge(
            query_embedding=query_embedding,
            qdrant_store=self.qdrant_store,
            user_id=self.user_id,
            agent_id=self.agent_id,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            top_k=top_k,
        )

    def delete_knowledge(self, kb_id: str) -> None:
        """Delete a knowledge base and all its chunks."""
        self.qdrant_store.delete_knowledge_chunks(kb_id)
        self.db.delete_knowledge_base(kb_id)

    def get_stats(self) -> dict:
        """Return statistics about the memory system."""
        kbs = self.db.load_knowledge_bases(self.user_id, self.agent_id)
        return {
            "memories": len(self.engine._memories),
            "nodes": len(self.engine.graph.nodes),
            "edges": len(self.engine.graph.edges),
            "anchors": list(self.engine.classifier.get_anchors().keys()),
            "knowledge_bases": len(kbs),
        }

    # --- Persistence ---

    def _persist_memory(self, record: MemoryRecord, sparse_data=None) -> None:
        """Persist a memory and its graph nodes/edges to Qdrant + SQLite."""
        # Persist memory to Qdrant
        sparse_indices = sparse_data[0] if sparse_data else None
        sparse_values = sparse_data[1] if sparse_data else None
        self.qdrant_store.save_memory(record, sparse_indices, sparse_values)

        # Persist memory metadata to SQLite
        self.db.save_memory(record)

        # Persist graph nodes to Qdrant
        for nid in record.node_ids:
            node = self.engine.graph.nodes.get(nid)
            if node:
                self.qdrant_store.save_node(node)

        # Edges always go to SQLite
        self._persist_graph()

    def _persist_graph(self) -> None:
        """Persist only dirty graph edges (incremental, always to SQLite)."""
        dirty = self.engine.graph.pop_dirty_edges()
        if dirty:
            self.db.save_edges_batch(dirty)

    def _load_from_db(self) -> None:
        """Load persisted memories and rebuild graph on startup."""
        # Load memories from Qdrant
        records = self.qdrant_store.load_memories(self.user_id)
        for record in records:
            self.engine.load_memory(record)

        # Load graph nodes from Qdrant, edges from SQLite
        nodes = self.qdrant_store.load_nodes()
        edges = self.db.load_edges()
        if nodes:
            rebuilt = rebuild_graph_from_db(nodes, edges, self.config)
            rebuilt.qdrant_store = self.qdrant_store
            self.engine.graph = rebuilt

        # Load custom anchors (always from SQLite)
        anchors = self.db.load_anchors(self.user_id)
        for name, texts in anchors:
            if isinstance(texts, list):
                for text in texts:
                    self.engine.classifier.add_anchor(
                        name, text, self.engine.embeddings.embed_sentence
                    )
            else:
                # Backward compat: single string from old DB
                self.engine.classifier.add_anchor(
                    name, texts, self.engine.embeddings.embed_sentence
                )

    def close(self) -> None:
        """Shutdown background threads and persist final state."""
        self._persist_graph()
        self._executor.shutdown(wait=True)
        self.qdrant_store.close()
