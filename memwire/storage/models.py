"""SQLAlchemy ORM models for persistent storage (metadata ledger)."""

from sqlalchemy import (
    Column, String, Float, Integer, Text, create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class MemoryModel(Base):
    """Memory metadata (no embedding blobs — vectors live in Qdrant)."""
    __tablename__ = "memories"

    memory_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=True, index=True)
    content = Column(Text, nullable=False)
    role = Column(String, nullable=False, default="user")
    category = Column(String, nullable=True)
    strength = Column(Float, default=1.0)
    timestamp = Column(Float, nullable=False)
    node_ids_json = Column(Text, default="[]")  # JSON list of node IDs
    created_at = Column(Float, nullable=False)
    access_count = Column(Integer, default=0)


class GraphNodeModel(Base):
    """Graph node metadata (no embedding blobs)."""
    __tablename__ = "graph_nodes"

    node_id = Column(String, primary_key=True)
    token = Column(String, nullable=False)
    memory_ids_json = Column(Text, default="[]")  # JSON list of memory IDs


class EdgeModel(Base):
    """Graph edge persisted to storage."""
    __tablename__ = "edges"

    source_id = Column(String, primary_key=True)
    target_id = Column(String, primary_key=True)
    weight = Column(Float, default=0.5)
    displacement_sim = Column(Float, default=0.0)


class AnchorModel(Base):
    """Classification anchor (no embedding blobs)."""
    __tablename__ = "anchors"

    name = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    texts_json = Column(Text, nullable=False)  # JSON list of anchor texts


class KnowledgeBaseModel(Base):
    """Knowledge base metadata."""
    __tablename__ = "knowledge_bases"

    kb_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    created_at = Column(Float, nullable=False)
    chunk_count = Column(Integer, default=0)


def create_all(database_url: str):
    """Create engine, tables, and return sessionmaker."""
    # In-memory SQLite needs StaticPool so all threads share one connection/DB
    if ":memory:" in database_url:
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            database_url, echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
