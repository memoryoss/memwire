"""Database manager: CRUD operations for metadata ledger (SQLite)."""

import json
import time
from typing import Optional

from sqlalchemy import Integer, desc, distinct, func
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
                org_id=record.org_id,
                workspace_id=record.workspace_id,
                app_id=record.app_id,
            )
            session.merge(model)
            session.commit()

    def load_memories(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        org_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> list[MemoryRecord]:
        """Load memory metadata. Returns records without embeddings."""
        with self._session() as session:
            query = session.query(MemoryModel).filter_by(user_id=user_id)
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            if org_id is not None:
                query = query.filter_by(org_id=org_id)
            if workspace_id is not None:
                query = query.filter_by(workspace_id=workspace_id)
            if app_id is not None:
                query = query.filter_by(app_id=app_id)
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
            org_id=m.org_id if m.org_id is not None else "",
            workspace_id=m.workspace_id,
            app_id=m.app_id,
        )

    def list_memories(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        org_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
        category: Optional[str] = None,
        role: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]:
        """Paginated list of memories with optional filters.

        All filter args default to None (= no filter on that field). Returns
        (records, total_matching_count) ordered by timestamp DESC.
        """
        with self._session() as session:
            query = session.query(MemoryModel)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            if org_id is not None:
                query = query.filter_by(org_id=org_id)
            if workspace_id is not None:
                query = query.filter_by(workspace_id=workspace_id)
            if app_id is not None:
                query = query.filter_by(app_id=app_id)
            if category is not None:
                query = query.filter_by(category=category)
            if role is not None:
                query = query.filter_by(role=role)
            if since is not None:
                query = query.filter(MemoryModel.timestamp >= since)
            if until is not None:
                query = query.filter(MemoryModel.timestamp <= until)
            if search:
                query = query.filter(MemoryModel.content.ilike(f"%{search}%"))
            total = query.count()
            rows = (
                query.order_by(desc(MemoryModel.timestamp))
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [self._model_to_record(r) for r in rows], total

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
                user_id=node.user_id,
                app_id=node.app_id,
                workspace_id=node.workspace_id,
            )
            session.merge(model)
            session.commit()

    def load_nodes(self, user_id: Optional[str] = None) -> list[dict]:
        """Load node metadata (no embeddings). Returns list of dicts."""
        with self._session() as session:
            query = session.query(GraphNodeModel)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            rows = query.all()
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
                user_id=edge.user_id,
            )
            session.merge(model)
            session.commit()

    def save_edges_batch(self, edges: list[GraphEdge]) -> None:
        """Batch-save edges using ORM merge (works with any SQL backend)."""
        with self._session() as session:
            for edge in edges:
                model = EdgeModel(
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    weight=edge.weight,
                    displacement_sim=edge.displacement_sim,
                    user_id=edge.user_id,
                )
                session.merge(model)
            session.commit()

    def load_edges(self, user_id: Optional[str] = None) -> list[GraphEdge]:
        with self._session() as session:
            query = session.query(EdgeModel)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            rows = query.all()
            return [
                GraphEdge(
                    source_id=r.source_id,
                    target_id=r.target_id,
                    weight=r.weight,
                    displacement_sim=r.displacement_sim,
                    user_id=getattr(r, 'user_id', ''),
                )
                for r in rows
            ]

    def load_edges_for_nodes(self, node_ids: set[str]) -> list[GraphEdge]:
        """Load only edges whose both endpoints are in *node_ids* (DB-level filter)."""
        if not node_ids:
            return []
        node_list = list(node_ids)
        with self._session() as session:
            rows = (
                session.query(EdgeModel)
                .filter(
                    EdgeModel.source_id.in_(node_list),
                    EdgeModel.target_id.in_(node_list),
                )
                .all()
            )
            return [
                GraphEdge(
                    source_id=r.source_id,
                    target_id=r.target_id,
                    weight=r.weight,
                    displacement_sim=r.displacement_sim,
                    user_id=r.user_id,
                )
                for r in rows
            ]

    # --- Anchor CRUD ---

    def save_anchor(
        self,
        name: str,
        user_id: str,
        texts,
        org_id: str = "default",
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> None:
        """Save anchor with texts as JSON list (no embedding blob)."""
        with self._session() as session:
            texts_list = texts if isinstance(texts, list) else [texts]
            model = AnchorModel(
                name=name,
                user_id=user_id,
                texts_json=json.dumps(texts_list),
                org_id=org_id,
                workspace_id=workspace_id,
                app_id=app_id,
            )
            session.merge(model)
            session.commit()

    def load_anchors(
        self,
        user_id: str,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> list[tuple[str, list[str]]]:
        """Returns list of (name, texts_list)."""
        with self._session() as session:
            query = session.query(AnchorModel).filter_by(user_id=user_id)
            if workspace_id is not None:
                query = query.filter_by(workspace_id=workspace_id)
            if app_id is not None:
                query = query.filter_by(app_id=app_id)
            rows = query.all()
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
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
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
                workspace_id=workspace_id,
                app_id=app_id,
            )
            session.merge(model)
            session.commit()

    def load_knowledge_bases(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> list[dict]:
        """Load knowledge bases for user/agent."""
        with self._session() as session:
            query = session.query(KnowledgeBaseModel).filter_by(user_id=user_id)
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            if workspace_id is not None:
                query = query.filter_by(workspace_id=workspace_id)
            if app_id is not None:
                query = query.filter_by(app_id=app_id)
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

    def list_knowledge_bases(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        app_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Paginated list of knowledge bases with optional filters."""
        with self._session() as session:
            query = session.query(KnowledgeBaseModel)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            if workspace_id is not None:
                query = query.filter_by(workspace_id=workspace_id)
            if app_id is not None:
                query = query.filter_by(app_id=app_id)
            if search:
                query = query.filter(KnowledgeBaseModel.name.ilike(f"%{search}%"))
            total = query.count()
            rows = (
                query.order_by(desc(KnowledgeBaseModel.created_at))
                .limit(limit)
                .offset(offset)
                .all()
            )
            items = [
                {
                    "kb_id": r.kb_id,
                    "user_id": r.user_id,
                    "agent_id": r.agent_id,
                    "name": r.name,
                    "description": r.description or "",
                    "created_at": r.created_at,
                    "chunk_count": r.chunk_count or 0,
                    "workspace_id": r.workspace_id,
                    "app_id": r.app_id,
                }
                for r in rows
            ]
            return items, total

    def dashboard_stats(self, org_id: Optional[str] = None) -> dict:
        """Aggregate stats across all users/agents in an org."""
        with self._session() as session:
            m_query = session.query(MemoryModel)
            if org_id is not None:
                m_query = m_query.filter_by(org_id=org_id)

            total_memories = m_query.count()
            distinct_users = m_query.with_entities(
                func.count(distinct(MemoryModel.user_id))
            ).scalar() or 0

            cat_rows = (
                m_query.with_entities(MemoryModel.category, func.count())
                .group_by(MemoryModel.category)
                .all()
            )
            by_category = {(c or "uncategorized"): n for c, n in cat_rows}

            role_rows = (
                m_query.with_entities(MemoryModel.role, func.count())
                .group_by(MemoryModel.role)
                .all()
            )
            by_role = {r: n for r, n in role_rows}

            # GraphNodeModel and EdgeModel have no org_id column — these are
            # always global counts regardless of org_id filter.
            total_nodes = session.query(GraphNodeModel).count()
            total_edges = session.query(EdgeModel).count()

            # KnowledgeBaseModel has no org_id column; scope approximately by
            # matching users that appear in the org's memories when org_id is set.
            kb_query = session.query(KnowledgeBaseModel)
            if org_id is not None:
                org_user_ids = (
                    session.query(MemoryModel.user_id)
                    .filter(MemoryModel.org_id == org_id)
                    .distinct()
                )
                kb_query = kb_query.filter(
                    KnowledgeBaseModel.user_id.in_(org_user_ids)
                )
            total_kbs = kb_query.count()

            a_query = session.query(AnchorModel)
            if org_id is not None:
                a_query = a_query.filter_by(org_id=org_id)
            total_anchors = a_query.count()

            now = time.time()
            days = 14
            ts_min = now - days * 86400
            day_bucket = func.cast(
                func.floor((MemoryModel.timestamp - ts_min) / 86400), Integer
            ).label("day_idx")
            ts_rows = (
                m_query.filter(MemoryModel.timestamp >= ts_min)
                .with_entities(day_bucket, func.count().label("cnt"))
                .group_by("day_idx")
                .all()
            )
            buckets = {}
            for row in ts_rows:
                idx = int(row.day_idx)
                if 0 <= idx < days:
                    buckets[idx] = row.cnt
            timeseries = [
                {"ts": int(ts_min + i * 86400), "count": buckets.get(i, 0)}
                for i in range(days)
            ]

            return {
                "total_memories": total_memories,
                "distinct_users": distinct_users,
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "total_knowledge_bases": total_kbs,
                "total_anchors": total_anchors,
                "by_category": by_category,
                "by_role": by_role,
                "timeseries": timeseries,
            }

    def recent_activity(self, limit: int = 50, org_id: Optional[str] = None) -> list[dict]:
        """Recent memory adds + KB ingests, merged and sorted by timestamp DESC."""
        with self._session() as session:
            m_query = session.query(MemoryModel)
            if org_id is not None:
                m_query = m_query.filter_by(org_id=org_id)
            memories = (
                m_query.order_by(desc(MemoryModel.timestamp)).limit(limit).all()
            )
            kb_query = session.query(KnowledgeBaseModel)
            kbs = (
                kb_query.order_by(desc(KnowledgeBaseModel.created_at))
                .limit(limit)
                .all()
            )
            items: list[dict] = []
            for m in memories:
                excerpt = (m.content[:80] + "...") if m.content and len(m.content) > 80 else (m.content or "")
                items.append({
                    "type": "memory_added",
                    "timestamp": m.timestamp,
                    "user_id": m.user_id,
                    "summary": excerpt,
                    "related_id": m.memory_id,
                    "role": m.role,
                    "category": m.category,
                })
            for kb in kbs:
                items.append({
                    "type": "knowledge_ingested",
                    "timestamp": kb.created_at,
                    "user_id": kb.user_id,
                    "summary": f"Ingested '{kb.name}' ({kb.chunk_count or 0} chunks)",
                    "related_id": kb.kb_id,
                    "role": None,
                    "category": None,
                })
            items.sort(key=lambda x: x["timestamp"], reverse=True)
            return items[:limit]

    def list_workspaces(self, org_id: Optional[str] = None) -> list[dict]:
        """List distinct workspace_ids with aggregate stats from memories."""
        with self._session() as session:
            query = session.query(MemoryModel)
            if org_id is not None:
                query = query.filter_by(org_id=org_id)
            rows = (
                query.with_entities(
                    MemoryModel.workspace_id,
                    func.count(MemoryModel.memory_id).label("memory_count"),
                    func.count(distinct(MemoryModel.user_id)).label("user_count"),
                    func.max(MemoryModel.timestamp).label("last_active"),
                )
                .group_by(MemoryModel.workspace_id)
                .all()
            )
            return [
                {
                    "workspace_id": ws,
                    "memory_count": int(mc),
                    "user_count": int(uc),
                    "last_active": float(la) if la is not None else 0.0,
                }
                for ws, mc, uc, la in rows
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
