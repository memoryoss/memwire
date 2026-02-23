"""
Knowledge Service

Manages per-agent knowledge bases using Agno's Knowledge + PgVector.
Follows the chatmemory-backend pattern (get_or_create_knowledge_base).

Table layout:
  agno.kb_{short}      — pgvector embeddings table (Agno/PgVector creates & owns)
  memwire.kb_documents — document metadata registry (we own for list/delete)
"""

import uuid
import logging
from typing import Optional, List, Dict, Tuple
from collections import OrderedDict
from io import BytesIO

from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector
from sqlalchemy import text

from app.config import settings
from app.services.llm_service import get_embedder
from app.db_session import SessionLocal

logger = logging.getLogger(__name__)

# LRU cache of Knowledge instances per agent_id
_knowledge_bases: OrderedDict[str, Knowledge] = OrderedDict()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _kb_table(agent_id: str) -> str:
    """Short KB table name — avoids PostgreSQL's 63-char identifier limit."""
    return f"kb_{agent_id.split('-')[0]}"


# ── Core KB factory ───────────────────────────────────────────────────────────


def get_or_create_knowledge_base(agent_id: str) -> Knowledge:
    """
    Get or create a pgvector-backed Knowledge instance for an agent.

    Mirrors chatmemory-backend's get_or_create_knowledge_base().
    PgVector auto-creates agno.kb_{short} with pgvector extension on first load.
    Knowledge instances are LRU-cached at MAX_KNOWLEDGE_BASES.
    """
    global _knowledge_bases

    if agent_id in _knowledge_bases:
        _knowledge_bases.move_to_end(agent_id)
        return _knowledge_bases[agent_id]

    table_name = _kb_table(agent_id)

    vector_db = PgVector(
        table_name=table_name,
        db_url=settings.DATABASE_URL,
        schema="agno",
        embedder=get_embedder(),
    )

    kb = Knowledge(
        vector_db=vector_db,
        max_results=5,
    )

    _knowledge_bases[agent_id] = kb
    _knowledge_bases.move_to_end(agent_id)

    # LRU eviction
    if len(_knowledge_bases) > settings.MAX_KNOWLEDGE_BASES:
        evicted, _ = _knowledge_bases.popitem(last=False)
        logger.debug(f"Evicted KB cache for agent_id={evicted}")

    logger.info(
        f"✓ Knowledge base ready for agent_id={agent_id} (table: agno.{table_name})"
    )
    return kb


def evict_knowledge_base(agent_id: str) -> None:
    """Remove a knowledge base from the in-process cache."""
    _knowledge_bases.pop(agent_id, None)


# ── Ingestion ──────────────────────────────────────────────────────────────────


def ingest_text(
    agent_id: str,
    content: str,
    doc_name: str,
    chunk_size: int = 1000,
    metadata: Optional[dict] = None,
) -> Tuple[str, int]:
    """Chunk and embed raw text into the agent's KB."""
    from agno.document import Document
    from agno.document.chunking.fixed import FixedSizeChunking

    doc_id = str(uuid.uuid4())
    meta = {
        **(metadata or {}),
        "doc_id": doc_id,
        "doc_name": doc_name,
        "source_type": "text",
    }

    chunker = FixedSizeChunking(chunk_size=chunk_size)
    doc = Document(id=doc_id, name=doc_name, content=content, meta_data=meta)
    chunks = chunker.chunk(doc)

    kb = get_or_create_knowledge_base(agent_id)
    kb.load_documents(chunks, upsert=True)

    _record_document(agent_id, doc_id, doc_name, "text", None, len(chunks))
    return doc_id, len(chunks)


def ingest_url(
    agent_id: str,
    url: str,
    doc_name: Optional[str] = None,
    chunk_size: int = 1000,
) -> Tuple[str, int]:
    """Scrape a URL and embed its content into the agent's KB."""
    import requests
    from bs4 import BeautifulSoup
    from agno.document import Document
    from agno.document.chunking.fixed import FixedSizeChunking

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    text_content = soup.get_text(separator="\n", strip=True)

    name = doc_name or url
    doc_id = str(uuid.uuid4())
    meta = {"doc_id": doc_id, "doc_name": name, "source_type": "url", "url": url}

    chunker = FixedSizeChunking(chunk_size=chunk_size)
    doc = Document(id=doc_id, name=name, content=text_content, meta_data=meta)
    chunks = chunker.chunk(doc)

    kb = get_or_create_knowledge_base(agent_id)
    kb.load_documents(chunks, upsert=True)

    _record_document(agent_id, doc_id, name, "url", url, len(chunks))
    return doc_id, len(chunks)


def ingest_file(
    agent_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    chunk_size: int = 1000,
) -> Tuple[str, int]:
    """Parse and embed a file (PDF, TXT, MD, CSV, JSON) into the agent's KB."""
    from agno.document.chunking.fixed import FixedSizeChunking
    from agno.document import Document

    doc_id = str(uuid.uuid4())
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        text_content = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext in ("txt", "md"):
        text_content = file_bytes.decode("utf-8", errors="ignore")
    elif ext == "json":
        import json as _json

        data = _json.loads(file_bytes)
        text_content = _json.dumps(data, indent=2)
    elif ext == "csv":
        import csv, io

        reader = csv.DictReader(
            io.StringIO(file_bytes.decode("utf-8", errors="ignore"))
        )
        text_content = "\n".join(str(row) for row in reader)
    else:
        text_content = file_bytes.decode("utf-8", errors="ignore")

    meta = {
        "doc_id": doc_id,
        "doc_name": filename,
        "source_type": "file",
        "filename": filename,
    }
    chunker = FixedSizeChunking(chunk_size=chunk_size)
    doc = Document(id=doc_id, name=filename, content=text_content, meta_data=meta)
    chunks = chunker.chunk(doc)

    kb = get_or_create_knowledge_base(agent_id)
    kb.load_documents(chunks, upsert=True)

    _record_document(agent_id, doc_id, filename, "file", filename, len(chunks))
    return doc_id, len(chunks)


# ── Search ────────────────────────────────────────────────────────────────────


def search_knowledge(agent_id: str, query: str, limit: int = 5) -> List[Dict]:
    """
    Vector similarity search over an agent's KB.
    Uses correct Agno API: Knowledge.search(query, max_results=limit).
    """
    kb = get_or_create_knowledge_base(agent_id)
    try:
        results = kb.search(query, max_results=limit)
    except Exception as exc:
        logger.warning(f"KB search failed for agent {agent_id}: {exc}")
        return []

    return [
        {
            "doc_id": r.meta_data.get("doc_id", ""),
            "doc_name": r.meta_data.get("doc_name", getattr(r, "name", "")),
            "chunk": r.content,
            "similarity": getattr(r, "score", 0.0),
            "metadata": r.meta_data,
        }
        for r in results
    ]


# ── Document registry ──────────────────────────────────────────────────────────


def list_documents(agent_id: str) -> List[Dict]:
    """List all documents registered for an agent (from memwire.kb_documents)."""
    with SessionLocal() as db:
        try:
            rows = db.execute(
                text(
                    """
                    SELECT doc_id, doc_name, source_type, source, chunk_count, created_at
                    FROM memwire.kb_documents
                    WHERE agent_id = :agent_id
                    ORDER BY created_at DESC
                    """
                ),
                {"agent_id": agent_id},
            ).fetchall()
        except Exception:
            return []

    return [
        {
            "doc_id": r[0],
            "doc_name": r[1],
            "source_type": r[2],
            "source": r[3],
            "chunk_count": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]


def delete_document(agent_id: str, doc_id: str) -> bool:
    """Delete a document's vectors and its metadata registry entry."""
    kb_table = _kb_table(agent_id)

    with SessionLocal() as db:
        try:
            # Delete embeddings (PgVector stores meta_data as JSON column)
            db.execute(
                text(
                    f"""
                    DELETE FROM agno."{kb_table}"
                    WHERE meta_data->>'doc_id' = :doc_id
                    """
                ),
                {"doc_id": doc_id},
            )
            # Delete metadata registry row
            db.execute(
                text(
                    "DELETE FROM memwire.kb_documents"
                    " WHERE agent_id = :a AND doc_id = :d"
                ),
                {"a": agent_id, "d": doc_id},
            )
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.warning(
                f"Failed to delete document {doc_id} for agent {agent_id}: {exc}"
            )
            return False


def delete_agent_knowledge(agent_id: str) -> None:
    """Drop the agent's vectordb table and remove all document records."""
    evict_knowledge_base(agent_id)
    kb_table = _kb_table(agent_id)

    with SessionLocal() as db:
        db.execute(text(f'DROP TABLE IF EXISTS agno."{kb_table}" CASCADE'))
        db.execute(
            text("DELETE FROM memwire.kb_documents WHERE agent_id = :a"),
            {"a": agent_id},
        )
        db.commit()

    logger.info(f"Deleted knowledge base for agent_id={agent_id}")


def _record_document(
    agent_id: str,
    doc_id: str,
    doc_name: str,
    source_type: str,
    source: Optional[str],
    chunk_count: int,
) -> None:
    """Upsert a document row into memwire.kb_documents."""
    with SessionLocal() as db:
        try:
            db.execute(
                text(
                    """
                    INSERT INTO memwire.kb_documents
                        (agent_id, doc_id, doc_name, source_type, source, chunk_count, created_at)
                    VALUES
                        (:a, :d, :dn, :st, :s, :cc, NOW())
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "a": agent_id,
                    "d": doc_id,
                    "dn": doc_name,
                    "st": source_type,
                    "s": source,
                    "cc": chunk_count,
                },
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.debug(f"Could not record document metadata: {exc}")
