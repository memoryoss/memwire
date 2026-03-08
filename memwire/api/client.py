"""MemWire — the explicit user-facing API."""

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from ..config import MemWireConfig
from ..core.engine import MemoryEngine
from ..core.recall import RecallEngine
from ..core.feedback import FeedbackProcessor
from ..core.graph import DisplacementGraph
from ..storage.database import DatabaseManager
from ..storage.qdrant_store import QdrantStore
from ..storage.vector_ops import find_similar_memories, rebuild_graph_from_db
from ..utils.types import RecallResult, MemoryRecord, KnowledgeChunk
from .formatter import MemoryFormatter

logger = logging.getLogger(__name__)


class MemWire:
    """Explicit API for vector-based memory. No automatic LLM interception.

    A single MemWire instance can serve an entire organization.
    User isolation via per-user graph caches, memory dicts, and hierarchy filters.
    """

    def __init__(
        self,
        config: Optional[MemWireConfig] = None,
    ):
        self.config = config or MemWireConfig()

        self.qdrant_store = QdrantStore(self.config)
        self.engine = MemoryEngine(self.config, qdrant_store=self.qdrant_store)
        self.recall_engine = RecallEngine(self.config)
        self.feedback_processor = FeedbackProcessor(self.config)
        self.formatter = MemoryFormatter()
        self.db = DatabaseManager(self.config)
        self._reranker = None
        self._executor = ThreadPoolExecutor(max_workers=self.config.background_threads)

        self._graphs: dict[str, DisplacementGraph] = {}  # per-user graph cache
        self._memories: dict[str, dict[str, MemoryRecord]] = {}  # per-user memory cache
        self._memory_nodes: dict[str, dict[str, list[str]]] = {}  # per-user node map
        self._last_recalls: dict[str, RecallResult] = {}  # per-user last recall
        self._lock = threading.Lock()  # guards cache init

    def _graph_key(self, user_id: str, app_id: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
        return f"{user_id}:{app_id or ''}:{workspace_id or ''}"

    def _get_graph(self, user_id: str, app_id: Optional[str] = None, workspace_id: Optional[str] = None) -> DisplacementGraph:
        """Lazy per-user graph loading."""
        key = self._graph_key(user_id, app_id, workspace_id)
        with self._lock:
            if key not in self._graphs:
                nodes = self.qdrant_store.load_nodes(
                    user_id=user_id, app_id=app_id, workspace_id=workspace_id,
                )
                edges = self.db.load_edges(user_id=user_id)
                graph = rebuild_graph_from_db(nodes, edges, self.config)
                graph.qdrant_store = self.qdrant_store
                self._graphs[key] = graph
            return self._graphs[key]

    def _get_user_memories(self, user_id: str, app_id: Optional[str] = None, workspace_id: Optional[str] = None) -> dict[str, MemoryRecord]:
        """Get or create per-user memory dict."""
        key = self._graph_key(user_id, app_id, workspace_id)
        with self._lock:
            if key not in self._memories:
                self._memories[key] = {}
            return self._memories[key]

    def _get_user_memory_nodes(self, user_id: str, app_id: Optional[str] = None, workspace_id: Optional[str] = None) -> dict[str, list[str]]:
        """Get or create per-user memory_id -> node_ids map."""
        key = self._graph_key(user_id, app_id, workspace_id)
        with self._lock:
            if key not in self._memory_nodes:
                self._memory_nodes[key] = {}
            return self._memory_nodes[key]

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

    def add(
        self,
        *,
        user_id: str,
        messages: list[dict[str, str]],
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> list[MemoryRecord]:
        """Add memories from message dicts. Each must have 'role' and 'content'."""
        org_id = self.config.org_id
        graph = self._get_graph(user_id, app_id, workspace_id)
        user_memories = self._get_user_memories(user_id, app_id, workspace_id)
        user_nodes = self._get_user_memory_nodes(user_id, app_id, workspace_id)

        records = []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "user")
            if not content.strip():
                continue
            record = self.engine.add_memory(
                content, role=role, user_id=user_id, agent_id=agent_id,
                org_id=org_id, app_id=app_id, workspace_id=workspace_id,
                graph=graph, memory_nodes=user_nodes,
            )
            user_memories[record.memory_id] = record
            records.append(record)

            sparse_data = None
            try:
                indices, values = self.engine.embeddings.embed_sparse(content)
                sparse_data = (indices, values)
            except Exception as e:
                logger.warning("Sparse embedding failed: %s", e)

            self._submit_bg(self._persist_memory, record, sparse_data, graph)

        return records

    def recall(
        self,
        query: str,
        *,
        user_id: str,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> RecallResult:
        """Recall relevant memory paths for a query."""
        graph = self._get_graph(user_id, app_id, workspace_id)
        user_memories = self._get_user_memories(user_id, app_id, workspace_id)
        query_embedding = self.engine.embeddings.embed_sentence(query)

        sparse_indices = None
        sparse_values = None
        try:
            sparse_indices, sparse_values = self.engine.embeddings.embed_sparse(query)
        except Exception as e:
            logger.warning("Sparse embedding failed for recall: %s", e)

        result = self.recall_engine.recall(
            query_embedding=query_embedding,
            graph=graph,
            memories=user_memories,
            query_text=query,
            qdrant_store=self.qdrant_store,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            user_id=user_id,
            agent_id=agent_id,
            app_id=app_id,
            workspace_id=workspace_id,
        )

        result.formatted = self.formatter.format(result)
        key = self._graph_key(user_id, app_id, workspace_id)
        self._last_recalls[key] = result
        return result

    def feedback(
        self,
        response: str,
        *,
        user_id: str,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, int]:
        """Provide feedback from LLM response to strengthen/weaken paths."""
        key = self._graph_key(user_id, app_id, workspace_id)
        last_recall = self._last_recalls.get(key)
        if not last_recall:
            return {"strengthened": 0, "weakened": 0}

        graph = self._get_graph(user_id, app_id, workspace_id)
        response_embedding = self.engine.embeddings.embed_sentence(response)
        stats = self.feedback_processor.process(
            response_embedding, last_recall, graph
        )

        # Persist only dirty edge changes asynchronously
        self._submit_bg(self._persist_graph, graph)
        return stats

    def search(
        self,
        query: str,
        *,
        user_id: str,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 10,
    ) -> list[tuple[MemoryRecord, float]]:
        """Search memories by similarity, optionally filtered by category."""
        user_memories = self._get_user_memories(user_id, app_id, workspace_id)
        query_embedding = self.engine.embeddings.embed_sentence(query)

        sparse_indices = None
        sparse_values = None
        try:
            sparse_indices, sparse_values = self.engine.embeddings.embed_sparse(query)
        except Exception as e:
            logger.warning("Sparse embedding failed for search: %s", e)

        results = find_similar_memories(
            query_embedding,
            list(user_memories.values()),
            top_k=top_k * 2 if self.config.use_reranking else top_k,
            category=category,
            qdrant_store=self.qdrant_store,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            user_id=user_id,
            agent_id=agent_id,
            memory_dict=user_memories,
            workspace_id=workspace_id,
            app_id=app_id,
        )

        # Optional cross-encoder reranking
        if self.config.use_reranking and results:
            reranker = self._get_reranker()
            results = reranker.rerank(query, results, top_k=top_k)

        return results[:top_k]

    def add_anchor(
        self,
        name: str,
        text: str,
        *,
        user_id: str,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> None:
        """Add or update a classification anchor."""
        self.engine.classifier.add_anchor(
            name, text, self.engine.embeddings.embed_sentence
        )
        # Save the full texts list so multi-text anchors survive restart
        texts = self.engine.classifier.get_anchors().get(name, [text])
        self._submit_bg(
            self.db.save_anchor, name, user_id, texts,
            self.config.org_id, workspace_id, app_id,
        )

    # --- Knowledge Base API ---

    def add_knowledge(
        self,
        name: str,
        chunks: list[dict],
        *,
        user_id: str,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> str:
        """Add a knowledge base. Each chunk dict has 'content' and optional 'metadata'.

        Returns kb_id.
        """
        kb_id = f"kb_{uuid.uuid4().hex[:12]}"

        # Save KB metadata to SQLite
        self.db.save_knowledge_base(
            kb_id=kb_id,
            user_id=user_id,
            name=name,
            agent_id=agent_id,
            chunk_count=len(chunks),
            workspace_id=workspace_id,
            app_id=app_id,
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
                user_id=user_id,
                content=content,
                agent_id=agent_id,
                metadata=metadata,
                sparse_indices=sparse_indices,
                sparse_values=sparse_values,
                workspace_id=workspace_id,
                app_id=app_id,
            )

        return kb_id

    def search_knowledge(
        self,
        query: str,
        *,
        user_id: str,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        top_k: int = 5,
    ) -> list[KnowledgeChunk]:
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
            user_id=user_id,
            agent_id=agent_id,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            top_k=top_k,
            app_id=app_id,
            workspace_id=workspace_id,
        )

    def delete_knowledge(self, kb_id: str) -> None:
        """Delete a knowledge base and all its chunks."""
        self.qdrant_store.delete_knowledge_chunks(kb_id)
        self.db.delete_knowledge_base(kb_id)

    def get_stats(
        self,
        *,
        user_id: str,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict:
        """Return statistics about the memory system."""
        graph = self._get_graph(user_id, app_id, workspace_id)
        user_memories = self._get_user_memories(user_id, app_id, workspace_id)
        kbs = self.db.load_knowledge_bases(user_id, agent_id,
                                           workspace_id=workspace_id, app_id=app_id)
        return {
            "memories": len(user_memories),
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "anchors": list(self.engine.classifier.get_anchors().keys()),
            "knowledge_bases": len(kbs),
        }

    # --- Persistence ---

    def _persist_memory(self, record: MemoryRecord, sparse_data=None, graph: Optional[DisplacementGraph] = None) -> None:
        """Persist a memory and its graph nodes/edges to Qdrant + SQLite."""
        # Persist memory to Qdrant
        sparse_indices = sparse_data[0] if sparse_data else None
        sparse_values = sparse_data[1] if sparse_data else None
        self.qdrant_store.save_memory(record, sparse_indices, sparse_values)

        # Persist memory metadata to SQLite
        self.db.save_memory(record)

        # Persist graph nodes to Qdrant
        target_graph = graph or self.engine.graph
        for nid in record.node_ids:
            node = target_graph.nodes.get(nid)
            if node:
                self.qdrant_store.save_node(node)

        # Edges always go to SQLite
        self._persist_graph(target_graph)

    def _persist_graph(self, graph: Optional[DisplacementGraph] = None) -> None:
        """Persist only dirty graph edges (incremental, always to SQLite)."""
        target_graph = graph or self.engine.graph
        dirty = target_graph.pop_dirty_edges()
        if dirty:
            self.db.save_edges_batch(dirty)

    def close(self) -> None:
        """Shutdown background threads and persist final state."""
        # Persist dirty edges from all cached graphs
        for graph in self._graphs.values():
            self._persist_graph(graph)
        self._persist_graph(self.engine.graph)
        self._executor.shutdown(wait=True)
        self.qdrant_store.close()
