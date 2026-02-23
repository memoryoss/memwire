"""
Context Service

Assembles a ready-to-inject context string from memory history
and knowledge base search results for a given user/agent/query.
"""

import logging
from typing import Optional

from app.config import settings
from app.services.memory_service import get_history, get_user_memories
from app.services.knowledge_service import search_knowledge

logger = logging.getLogger(__name__)


def build_context_snapshot(
    agent_id: str,
    user_id: str,
    query: str,
    history_turns: int = 10,
    include_knowledge: bool = True,
    knowledge_results: int = 5,
    max_tokens: Optional[int] = None,
    session_id: Optional[str] = None,
) -> dict:
    """
    Assemble a context string from memory + knowledge for prompt injection.

    Returns:
        {
            "context": str,
            "memory_hits": int,
            "knowledge_hits": int,
            "token_estimate": int,
        }
    """
    token_budget = max_tokens or settings.DEFAULT_MAX_CONTEXT_TOKENS
    parts = []
    memory_hits = 0
    knowledge_hits = 0

    # ── Semantic Memories (Agno MemoryManager) ────────────────
    memories = get_history(
        agent_id=agent_id,
        user_id=user_id,
        limit=history_turns,
        session_id=session_id,
    )

    if memories:
        mem_lines = ["[User Memories]"]
        for m in memories:
            topics_str = f" [{', '.join(m['topics'])}]" if m.get("topics") else ""
            mem_lines.append(f"- {m['memory']}{topics_str}")
        parts.append("\n".join(mem_lines))
        memory_hits = len(memories)

    # ── Knowledge Base ────────────────────────────────────────
    if include_knowledge and query:
        kb_results = search_knowledge(
            agent_id=agent_id,
            query=query,
            limit=knowledge_results,
        )
        if kb_results:
            kb_lines = ["[Relevant Knowledge]"]
            for r in kb_results:
                kb_lines.append(f"- {r['chunk'].strip()}")
            parts.append("\n".join(kb_lines))
            knowledge_hits = len(kb_results)

    context = "\n\n".join(parts)

    # Rough token estimate: ~4 chars per token
    token_estimate = len(context) // 4

    # Trim if over budget (simple character-based truncation)
    max_chars = token_budget * 4
    if len(context) > max_chars:
        context = context[:max_chars] + "\n[...context truncated to fit token budget]"
        token_estimate = token_budget

    return {
        "context": context,
        "memory_hits": memory_hits,
        "knowledge_hits": knowledge_hits,
        "token_estimate": token_estimate,
    }
