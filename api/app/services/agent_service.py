"""
Agent Service — Agno Agent per agent_id

Creates fresh Agno Agent instances per call, following the chatmemory-backend pattern.

PostgresDb and MemoryManager are lightweight wrappers with no persistent state.
Actual DB connections are pooled at the SQLAlchemy engine level, so creating
them fresh on every call is trivial — no in-memory cache needed.

Reference: chatmemory-backend/app/services/agent_service.py get_memory_db()
  "PostgresDb is a lightweight wrapper (~1KB) that doesn't maintain connections.
   No caching needed - creation is trivial."
"""

import logging
from typing import Optional

from agno.agent import Agent
from agno.memory import MemoryManager
from agno.db.postgres import PostgresDb

from app.config import settings
from app.services.llm_service import get_model
from app.services.knowledge_service import get_or_create_knowledge_base

logger = logging.getLogger(__name__)

_MEMORY_SYSTEM_MESSAGE = (
    "Extract and remember key facts, user preferences, and important context "
    "from this conversation. Focus on information that will be useful in "
    "future interactions."
)


# ── Table naming ─────────────────────────────────────────────────────────────


def _mem_table(agent_id: str) -> str:
    # Must match memory_service.get_memory_db() — Agno creates tables with these names
    return f"memories_{agent_id.split('-')[0]}"


def _sess_table(agent_id: str) -> str:
    return f"sessions_{agent_id.split('-')[0]}"


# ── DB / Manager factories ────────────────────────────────────────────────────


def get_memory_db(agent_id: str) -> PostgresDb:
    """
    Create a fresh PostgresDb instance for an agent.

    PostgresDb is a lightweight config wrapper (~1KB) — it holds no connections.
    Real connections come from SQLAlchemy's pool. Creating it fresh per call
    is intentional (mirrors chatmemory-backend).
    """
    return PostgresDb(
        db_url=settings.DATABASE_URL,
        memory_table=_mem_table(agent_id),
        session_table=_sess_table(agent_id),
        db_schema="agno",
    )


def get_memory_manager(agent_id: str) -> MemoryManager:
    """Create a fresh MemoryManager backed by this agent's DB tables."""
    return MemoryManager(
        db=get_memory_db(agent_id),
        model=get_model(),
        system_message=_MEMORY_SYSTEM_MESSAGE,
    )


# ── Agent factory ─────────────────────────────────────────────────────────────


def make_agent(agent_id: str, user_id: str) -> Agent:
    """
    Create a fresh Agno Agent for a specific (agent_id, user_id) pair.

    A new instance is always created — no caching — so user_id is always
    correctly scoped and there are no cross-user memory leaks.

    Mirrors chatmemory-backend generate_reply():
      memory_db      = get_memory_db(org_id)        # fresh each call
      memory_manager = MemoryManager(db=memory_db)  # fresh each call
      agent          = Agent(...)                   # fresh each call
    """
    memory_db = get_memory_db(agent_id)
    memory_manager = MemoryManager(
        db=memory_db,
        model=get_model(),
        system_message=_MEMORY_SYSTEM_MESSAGE,
    )

    try:
        knowledge = get_or_create_knowledge_base(agent_id)
    except Exception as exc:
        logger.warning(f"Could not load knowledge base for agent_id={agent_id}: {exc}")
        knowledge = None

    return Agent(
        model=get_model(),
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        db=memory_db,
        memory_manager=memory_manager,
        enable_user_memories=True,
        enable_session_summaries=True,
        search_session_history=True,
        markdown=False,
        user_id=user_id,
    )
