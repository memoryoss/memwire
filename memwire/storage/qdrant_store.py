"""Qdrant-based vector storage with hybrid (dense + sparse) search."""

import json
import uuid
from typing import Optional

import numpy as np
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    SparseVector,
    Prefetch,
    FusionQuery,
    Fusion,
    Filter,
    FieldCondition,
    MatchValue,
)

from ..config import MemWireConfig
from ..utils.types import MemoryRecord, GraphNode


class QdrantStore:
    """Qdrant local storage with hybrid dense + sparse search."""

    def __init__(self, config: MemWireConfig):
        self.config = config

        # Collection names with optional prefix for app isolation
        prefix = config.qdrant_collection_prefix
        self.memories_collection = f"{prefix}memories"
        self.graph_nodes_collection = f"{prefix}graph_nodes"
        self.knowledge_collection = f"{prefix}knowledge_chunks"

        # Priority: url (remote/local server) > path (embedded) > default embedded
        if config.qdrant_url:
            self._client = QdrantClient(
                url=config.qdrant_url,
                api_key=config.qdrant_api_key,
            )
        elif config.qdrant_path == ":memory:":
            self._client = QdrantClient(location=":memory:")
        elif config.qdrant_path:
            self._client = QdrantClient(path=config.qdrant_path)
        else:
            path = f"qdrant_data_{config.org_id}"
            self._client = QdrantClient(path=path)

        self._ensure_collections()

    def _str_to_uuid(self, string_id: str) -> str:
        """Deterministic UUID mapping from string IDs."""
        return str(uuid.uuid5(uuid.NAMESPACE_URL, string_id))

    def _ensure_collections(self) -> None:
        """Create collections if they don't exist."""
        existing = [c.name for c in self._client.get_collections().collections]

        if self.memories_collection not in existing:
            self._client.create_collection(
                collection_name=self.memories_collection,
                vectors_config={
                    "dense": VectorParams(
                        size=self.config.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False),
                    ),
                },
            )

        if self.graph_nodes_collection not in existing:
            self._client.create_collection(
                collection_name=self.graph_nodes_collection,
                vectors_config=VectorParams(
                    size=self.config.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )

        if self.knowledge_collection not in existing:
            self._client.create_collection(
                collection_name=self.knowledge_collection,
                vectors_config={
                    "dense": VectorParams(
                        size=self.config.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False),
                    ),
                },
            )

    # --- Memory operations ---

    def save_memory(
        self,
        record: MemoryRecord,
        sparse_indices: Optional[np.ndarray] = None,
        sparse_values: Optional[np.ndarray] = None,
    ) -> None:
        """Upsert a memory record into the memories collection."""
        point_id = self._str_to_uuid(record.memory_id)

        vectors = {
            "dense": record.embedding.tolist(),
        }

        sparse_vectors = {}
        if sparse_indices is not None and sparse_values is not None:
            sparse_vectors["sparse"] = SparseVector(
                indices=sparse_indices.tolist(),
                values=sparse_values.tolist(),
            )

        payload = {
            "memory_id_str": record.memory_id,
            "user_id": record.user_id,
            "agent_id": record.agent_id or "",
            "content": record.content,
            "role": record.role,
            "category": record.category or "",
            "strength": record.strength,
            "timestamp": record.timestamp,
            "node_ids": json.dumps(record.node_ids),
            "access_count": record.access_count,
            "org_id": record.org_id,
            "workspace_id": record.workspace_id or "",
            "app_id": record.app_id or "",
        }

        if sparse_vectors:
            point = PointStruct(
                id=point_id,
                vector={**vectors, **sparse_vectors},
                payload=payload,
            )
        else:
            point = PointStruct(
                id=point_id,
                vector=vectors,
                payload=payload,
            )

        self._client.upsert(
            collection_name=self.memories_collection,
            points=[point],
        )

    def load_memories(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> list[MemoryRecord]:
        """Load all memories for a user (optionally filtered by agent_id, app_id, workspace_id)."""
        records = []
        offset = None

        # Build filter conditions
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        if agent_id is not None:
            must_conditions.append(
                FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
            )
        if app_id is not None:
            must_conditions.append(
                FieldCondition(key="app_id", match=MatchValue(value=app_id))
            )
        if workspace_id is not None:
            must_conditions.append(
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
            )

        while True:
            result = self._client.scroll(
                collection_name=self.memories_collection,
                scroll_filter=Filter(must=must_conditions),
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=["dense"],
            )
            points, next_offset = result

            for point in points:
                payload = point.payload
                dense_vec = point.vector.get("dense", [])
                records.append(MemoryRecord(
                    memory_id=payload["memory_id_str"],
                    user_id=payload["user_id"],
                    content=payload["content"],
                    role=payload["role"],
                    embedding=np.array(dense_vec, dtype=np.float32),
                    category=payload.get("category") or None,
                    strength=payload.get("strength", 1.0),
                    timestamp=payload.get("timestamp", 0.0),
                    node_ids=json.loads(payload.get("node_ids", "[]")),
                    agent_id=payload.get("agent_id") or None,
                    access_count=payload.get("access_count", 0),
                    org_id=payload.get("org_id", ""),
                    workspace_id=payload.get("workspace_id") or None,
                    app_id=payload.get("app_id") or None,
                ))

            if next_offset is None:
                break
            offset = next_offset

        return records

    # --- Graph node operations ---

    def save_node(self, node: GraphNode) -> None:
        """Upsert a graph node into the graph_nodes collection."""
        point_id = self._str_to_uuid(node.node_id)

        self._client.upsert(
            collection_name=self.graph_nodes_collection,
            points=[PointStruct(
                id=point_id,
                vector=node.embedding.tolist(),
                payload={
                    "node_id_str": node.node_id,
                    "token": node.token,
                    "memory_ids": json.dumps(node.memory_ids),
                    "user_id": node.user_id,
                    "app_id": node.app_id or "",
                    "workspace_id": node.workspace_id or "",
                },
            )],
        )

    def load_nodes(
        self,
        *,
        user_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> list[GraphNode]:
        """Load graph nodes, optionally filtered by user/app/workspace."""
        nodes = []
        offset = None

        must_conditions = []
        if user_id is not None:
            must_conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )
        if app_id is not None:
            must_conditions.append(
                FieldCondition(key="app_id", match=MatchValue(value=app_id))
            )
        if workspace_id is not None:
            must_conditions.append(
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
            )
        scroll_filter = Filter(must=must_conditions) if must_conditions else None

        while True:
            result = self._client.scroll(
                collection_name=self.graph_nodes_collection,
                scroll_filter=scroll_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            points, next_offset = result

            for point in points:
                payload = point.payload
                nodes.append(GraphNode(
                    node_id=payload["node_id_str"],
                    token=payload["token"],
                    embedding=np.array(point.vector, dtype=np.float32),
                    memory_ids=json.loads(payload.get("memory_ids", "[]")),
                    user_id=payload.get("user_id", ""),
                    app_id=payload.get("app_id") or None,
                    workspace_id=payload.get("workspace_id") or None,
                ))

            if next_offset is None:
                break
            offset = next_offset

        return nodes

    # --- Search operations ---

    def hybrid_search(
        self,
        dense_embedding: np.ndarray,
        sparse_indices: Optional[np.ndarray] = None,
        sparse_values: Optional[np.ndarray] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 10,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> list[tuple[str, float, dict]]:
        """Hybrid search using dense + sparse with RRF fusion.

        Returns list of (memory_id_str, score, payload) tuples.
        """
        # Build filter
        must_conditions = []
        if user_id:
            must_conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )
        if agent_id is not None:
            must_conditions.append(
                FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
            )
        if category:
            must_conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category))
            )
        if workspace_id is not None:
            must_conditions.append(
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
            )
        if app_id is not None:
            must_conditions.append(
                FieldCondition(key="app_id", match=MatchValue(value=app_id))
            )
        search_filter = Filter(must=must_conditions) if must_conditions else None

        # If we have sparse vectors, do hybrid search
        has_sparse = (
            sparse_indices is not None
            and sparse_values is not None
            and len(sparse_indices) > 0
        )

        if has_sparse and self.config.use_hybrid_search:
            prefetch_list = [
                Prefetch(
                    query=dense_embedding.tolist(),
                    using="dense",
                    limit=top_k * 2,
                    filter=search_filter,
                ),
                Prefetch(
                    query=SparseVector(
                        indices=sparse_indices.tolist(),
                        values=sparse_values.tolist(),
                    ),
                    using="sparse",
                    limit=top_k * 2,
                    filter=search_filter,
                ),
            ]

            results = self._client.query_points(
                collection_name=self.memories_collection,
                prefetch=prefetch_list,
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
                with_payload=True,
                with_vectors=["dense"],
            )
        else:
            # Dense-only search
            results = self._client.query_points(
                collection_name=self.memories_collection,
                query=dense_embedding.tolist(),
                using="dense",
                limit=top_k,
                query_filter=search_filter,
                with_payload=True,
                with_vectors=["dense"],
            )

        output = []
        for point in results.points:
            memory_id_str = point.payload.get("memory_id_str", "")
            output.append((memory_id_str, point.score, point.payload))

        return output

    def search_nodes(
        self,
        embedding: np.ndarray,
        top_k: int = 5,
        *,
        user_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> list[tuple[str, float]]:
        """Dense search on graph_nodes collection.

        Returns list of (node_id_str, score) tuples.
        """
        must_conditions = []
        if user_id is not None:
            must_conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )
        if app_id is not None:
            must_conditions.append(
                FieldCondition(key="app_id", match=MatchValue(value=app_id))
            )
        if workspace_id is not None:
            must_conditions.append(
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
            )
        search_filter = Filter(must=must_conditions) if must_conditions else None

        results = self._client.query_points(
            collection_name=self.graph_nodes_collection,
            query=embedding.tolist(),
            limit=top_k,
            with_payload=True,
            query_filter=search_filter,
        )

        output = []
        for point in results.points:
            node_id_str = point.payload.get("node_id_str", "")
            output.append((node_id_str, point.score))

        return output

    # --- Knowledge chunk operations ---

    def save_knowledge_chunk(
        self,
        chunk_id: str,
        dense_embedding: np.ndarray,
        kb_id: str,
        user_id: str,
        content: str,
        agent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        sparse_indices: Optional[np.ndarray] = None,
        sparse_values: Optional[np.ndarray] = None,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> None:
        """Upsert a knowledge chunk into the knowledge_chunks collection."""
        point_id = self._str_to_uuid(chunk_id)

        vectors = {"dense": dense_embedding.tolist()}

        sparse_vectors = {}
        if sparse_indices is not None and sparse_values is not None:
            sparse_vectors["sparse"] = SparseVector(
                indices=sparse_indices.tolist(),
                values=sparse_values.tolist(),
            )

        payload = {
            "chunk_id_str": chunk_id,
            "kb_id": kb_id,
            "user_id": user_id,
            "agent_id": agent_id or "",
            "content": content,
            "metadata": json.dumps(metadata or {}),
            "workspace_id": workspace_id or "",
            "app_id": app_id or "",
        }

        if sparse_vectors:
            point = PointStruct(
                id=point_id,
                vector={**vectors, **sparse_vectors},
                payload=payload,
            )
        else:
            point = PointStruct(
                id=point_id,
                vector=vectors,
                payload=payload,
            )

        self._client.upsert(
            collection_name=self.knowledge_collection,
            points=[point],
        )

    def search_knowledge(
        self,
        dense_embedding: np.ndarray,
        user_id: str,
        agent_id: Optional[str] = None,
        sparse_indices: Optional[np.ndarray] = None,
        sparse_values: Optional[np.ndarray] = None,
        top_k: int = 5,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> list[tuple[str, float, dict]]:
        """Hybrid search on knowledge_chunks collection.

        Returns list of (chunk_id_str, score, payload) tuples.
        """
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        if agent_id is not None:
            must_conditions.append(
                FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
            )
        if workspace_id is not None:
            must_conditions.append(
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
            )
        if app_id is not None:
            must_conditions.append(
                FieldCondition(key="app_id", match=MatchValue(value=app_id))
            )
        search_filter = Filter(must=must_conditions)

        has_sparse = (
            sparse_indices is not None
            and sparse_values is not None
            and len(sparse_indices) > 0
        )

        if has_sparse and self.config.use_hybrid_search:
            prefetch_list = [
                Prefetch(
                    query=dense_embedding.tolist(),
                    using="dense",
                    limit=top_k * 2,
                    filter=search_filter,
                ),
                Prefetch(
                    query=SparseVector(
                        indices=sparse_indices.tolist(),
                        values=sparse_values.tolist(),
                    ),
                    using="sparse",
                    limit=top_k * 2,
                    filter=search_filter,
                ),
            ]
            results = self._client.query_points(
                collection_name=self.knowledge_collection,
                prefetch=prefetch_list,
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
                with_payload=True,
            )
        else:
            results = self._client.query_points(
                collection_name=self.knowledge_collection,
                query=dense_embedding.tolist(),
                using="dense",
                limit=top_k,
                query_filter=search_filter,
                with_payload=True,
            )

        output = []
        for point in results.points:
            chunk_id_str = point.payload.get("chunk_id_str", "")
            output.append((chunk_id_str, point.score, point.payload))

        return output

    def has_knowledge(self, user_id: str, agent_id: Optional[str] = None) -> bool:
        """Check if knowledge_chunks collection has any points for user/agent."""
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        if agent_id is not None:
            must_conditions.append(
                FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
            )

        result = self._client.count(
            collection_name=self.knowledge_collection,
            count_filter=Filter(must=must_conditions),
            exact=False,
        )
        return result.count > 0

    def delete_knowledge_chunks(self, kb_id: str) -> None:
        """Delete all chunks for a given kb_id."""
        self._client.delete(
            collection_name=self.knowledge_collection,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="kb_id", match=MatchValue(value=kb_id))]
                )
            ),
        )

    def close(self) -> None:
        """Close the Qdrant client."""
        self._client.close()
