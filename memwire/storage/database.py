"""Database manager: CRUD operations for metadata ledger (SQLite)."""

import json
import time
from typing import Optional

from sqlalchemy.orm import Session

from ..config import MemWireConfig
from ..utils.types import MemoryRecord, GraphNode, GraphEdge
from .models import (
    MemoryModel, GraphNodeModel, EdgeModel, AnchorModel,
    KnowledgeBaseModel, create_all,
)

import numpy as np


class DatabaseManager:
    """Manages all database operations (metadata only — no embedding blobs)."""

    def __init__(self, config: MemWireConfig):
        self.config = config
        self._SessionFactory = create_all(config.get_database_url())

    def _session(self) -> Session:
        return self._SessionFactory()

    # --- Memory CRUD ---

    def save_memory(self, record: MemoryRecord) -> None:
        with self._session() as session:
            model = MemoryModel(
                memory_id=record.memory_id,
                user_id=record.user_id,
                agent_id=record.agent_id,
                content=record.content,
                role=record.role,
                category=record.category,
                strength=record.strength,
                timestamp=record.timestamp,
                node_ids_json=json.dumps(record.node_ids),
                created_at=record.timestamp,
                access_count=record.access_count,
            )
            session.merge(model)
            session.commit()

    def load_memories(self, user_id: str, agent_id: Optional[str] = None) -> list[MemoryRecord]:
        """Load memory metadata. Returns records without embeddings."""
        with self._session() as session:
            query = session.query(MemoryModel).filter_by(user_id=user_id)
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            rows = query.all()
            return [self._model_to_record(r) for r in rows]

    def _model_to_record(self, m: MemoryModel) -> MemoryRecord:
        return MemoryRecord(
            memory_id=m.memory_id,
            user_id=m.user_id,
            content=m.content,
            role=m.role,
            embedding=np.zeros(self.config.embedding_dim, dtype=np.float32),
            category=m.category,
            strength=m.strength,
            timestamp=m.timestamp,
            node_ids=json.loads(m.node_ids_json),
            agent_id=m.agent_id,
            access_count=m.access_count if m.access_count is not None else 0,
        )

    def update_memory_strength(self, memory_id: str, strength: float) -> None:
        with self._session() as session:
            row = session.query(MemoryModel).filter_by(memory_id=memory_id).first()
            if row:
                row.strength = strength
                session.commit()

    def increment_access_count(self, memory_id: str) -> None:
        """Bump access_count on a memory."""
        with self._session() as session:
            row = session.query(MemoryModel).filter_by(memory_id=memory_id).first()
            if row:
                row.access_count = (row.access_count or 0) + 1
                session.commit()

    # --- Graph Node CRUD ---

    def save_node(self, node: GraphNode) -> None:
        with self._session() as session:
            model = GraphNodeModel(
                node_id=node.node_id,
                token=node.token,
                memory_ids_json=json.dumps(node.memory_ids),
            )
            session.merge(model)
            session.commit()

    def load_nodes(self) -> list[dict]:
        """Load node metadata (no embeddings). Returns list of dicts."""
        with self._session() as session:
            rows = session.query(GraphNodeModel).all()
            return [
                {
                    "node_id": r.node_id,
                    "token": r.token,
                    "memory_ids": json.loads(r.memory_ids_json),
                }
                for r in rows
            ]

    # --- Edge CRUD ---

    def save_edge(self, edge: GraphEdge) -> None:
        with self._session() as session:
            model = EdgeModel(
                source_id=edge.source_id,
                target_id=edge.target_id,
                weight=edge.weight,
                displacement_sim=edge.displacement_sim,
            )
            session.merge(model)
            session.commit()

    def save_edges_batch(self, edges: list[GraphEdge]) -> None:
        from sqlalchemy import text
        with self._session() as session:
            for edge in edges:
                session.execute(
                    text(
                        "INSERT OR REPLACE INTO edges "
                        "(source_id, target_id, weight, displacement_sim) "
                        "VALUES (:src, :tgt, :w, :ds)"
                    ),
                    {"src": edge.source_id, "tgt": edge.target_id,
                     "w": edge.weight, "ds": edge.displacement_sim},
                )
            session.commit()

    def load_edges(self) -> list[GraphEdge]:
        with self._session() as session:
            rows = session.query(EdgeModel).all()
            return [
                GraphEdge(
                    source_id=r.source_id,
                    target_id=r.target_id,
                    weight=r.weight,
                    displacement_sim=r.displacement_sim,
                )
                for r in rows
            ]

    # --- Anchor CRUD ---

    def save_anchor(self, name: str, user_id: str, texts) -> None:
        """Save anchor with texts as JSON list (no embedding blob)."""
        with self._session() as session:
            texts_list = texts if isinstance(texts, list) else [texts]
            model = AnchorModel(
                name=name,
                user_id=user_id,
                texts_json=json.dumps(texts_list),
            )
            session.merge(model)
            session.commit()

    def load_anchors(self, user_id: str) -> list[tuple[str, list[str]]]:
        """Returns list of (name, texts_list)."""
        with self._session() as session:
            rows = session.query(AnchorModel).filter_by(user_id=user_id).all()
            return [
                (r.name, json.loads(r.texts_json))
                for r in rows
            ]

    # --- Knowledge Base CRUD ---

    def save_knowledge_base(
        self,
        kb_id: str,
        user_id: str,
        name: str,
        agent_id: Optional[str] = None,
        description: str = "",
        chunk_count: int = 0,
    ) -> None:
        """Save knowledge base metadata."""
        with self._session() as session:
            model = KnowledgeBaseModel(
                kb_id=kb_id,
                user_id=user_id,
                agent_id=agent_id,
                name=name,
                description=description,
                created_at=time.time(),
                chunk_count=chunk_count,
            )
            session.merge(model)
            session.commit()

    def load_knowledge_bases(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
    ) -> list[dict]:
        """Load knowledge bases for user/agent."""
        with self._session() as session:
            query = session.query(KnowledgeBaseModel).filter_by(user_id=user_id)
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            rows = query.all()
            return [
                {
                    "kb_id": r.kb_id,
                    "user_id": r.user_id,
                    "agent_id": r.agent_id,
                    "name": r.name,
                    "description": r.description,
                    "created_at": r.created_at,
                    "chunk_count": r.chunk_count,
                }
                for r in rows
            ]

    def delete_knowledge_base(self, kb_id: str) -> None:
        """Remove a knowledge base record."""
        with self._session() as session:
            session.query(KnowledgeBaseModel).filter_by(kb_id=kb_id).delete()
            session.commit()

    def update_knowledge_base_chunk_count(self, kb_id: str, chunk_count: int) -> None:
        """Update the chunk count for a knowledge base."""
        with self._session() as session:
            row = session.query(KnowledgeBaseModel).filter_by(kb_id=kb_id).first()
            if row:
                row.chunk_count = chunk_count
                session.commit()
