"""MemWire REST API — three developer-facing endpoints.

POST /v1/memory         — store messages into memory
POST /v1/memory/recall  — recall relevant context for a query
POST /v1/memory/search  — search memories by semantic similarity
"""

import logging
import os
import sys
import io
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Suppress noisy model-download output on startup
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")

from dotenv import load_dotenv

load_dotenv()

from memwire import MemWire, MemWireConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global MemWire instance (shared across requests, user-isolated at query time)
# ---------------------------------------------------------------------------
_memory: Optional[MemWire] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _memory
    print("Loading MemWire...", end=" ", flush=True)
    _stderr = sys.stderr
    sys.stderr = io.StringIO()
    logging.disable(logging.WARNING)
    try:
        qdrant_url = os.getenv("QDRANT_URL")
        config = MemWireConfig(
            org_id=os.getenv("ORG_ID", "default"),
            database_url=os.getenv("DATABASE_URL", "sqlite:////data/memwire.db"),
            qdrant_url=qdrant_url,
            qdrant_path=None
            if qdrant_url
            else os.getenv("QDRANT_PATH", "/data/qdrant"),
            qdrant_collection_prefix=os.getenv("QDRANT_COLLECTION_PREFIX", "mw_"),
        )
        _memory = MemWire(config=config)
    finally:
        sys.stderr = _stderr
        logging.disable(logging.NOTSET)
    print("ready.")
    yield
    print("Shutting down MemWire...", end=" ", flush=True)
    _memory.close()
    print("done.")


app = FastAPI(
    title="MemWire API",
    description="Persistent AI memory infrastructure — store, recall, and search.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: str
    content: str


class StoreRequest(BaseModel):
    user_id: str
    messages: list[Message]
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None
    agent_id: Optional[str] = None


class StoreResponse(BaseModel):
    stored: int
    memory_ids: list[str]


class RecallRequest(BaseModel):
    user_id: str
    query: str
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None
    agent_id: Optional[str] = None
    top_k: int = 5


class RecallResponse(BaseModel):
    context: str
    paths: int
    knowledge: list[str]


class SearchRequest(BaseModel):
    user_id: str
    query: str
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None
    agent_id: Optional[str] = None
    top_k: int = 10
    category: Optional[str] = None


class SearchResult(BaseModel):
    memory_id: str
    content: str
    category: Optional[str]
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]


class KnowledgeChunkInput(BaseModel):
    content: str
    metadata: dict = {}


class AddKnowledgeRequest(BaseModel):
    user_id: str
    name: str
    chunks: list[KnowledgeChunkInput]
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None


class AddKnowledgeResponse(BaseModel):
    kb_id: str
    chunks_stored: int


class KnowledgeSearchRequest(BaseModel):
    user_id: str
    query: str
    agent_id: Optional[str] = None
    app_id: Optional[str] = None
    workspace_id: Optional[str] = None
    top_k: int = 5


class KnowledgeChunkResult(BaseModel):
    chunk_id: str
    kb_id: str
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    chunks: list[KnowledgeChunkResult]


class DeleteKnowledgeResponse(BaseModel):
    deleted: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/v1/memory", response_model=StoreResponse, summary="Store memory")
def store_memory(req: StoreRequest):
    """Store one or more messages into the user's memory."""
    records = _memory.add(
        user_id=req.user_id,
        messages=[m.model_dump() for m in req.messages],
        app_id=req.app_id,
        workspace_id=req.workspace_id,
        agent_id=req.agent_id,
    )
    return StoreResponse(
        stored=len(records),
        memory_ids=[r.memory_id for r in records],
    )


@app.post(
    "/v1/memory/recall", response_model=RecallResponse, summary="Recall memory context"
)
def recall_memory(req: RecallRequest):
    """Recall the most relevant memory context for a natural-language query."""
    result = _memory.recall(
        req.query,
        user_id=req.user_id,
        app_id=req.app_id,
        workspace_id=req.workspace_id,
        agent_id=req.agent_id,
    )
    knowledge_texts = [k.content for k in result.knowledge] if result.knowledge else []
    return RecallResponse(
        context=result.formatted or "",
        paths=len(result.supporting) if result.supporting else 0,
        knowledge=knowledge_texts,
    )


@app.post("/v1/memory/search", response_model=SearchResponse, summary="Search memories")
def search_memory(req: SearchRequest):
    """Search memories by semantic similarity, optionally filtered by category."""
    hits = _memory.search(
        req.query,
        user_id=req.user_id,
        app_id=req.app_id,
        workspace_id=req.workspace_id,
        agent_id=req.agent_id,
        top_k=req.top_k,
        category=req.category,
    )
    return SearchResponse(
        results=[
            SearchResult(
                memory_id=record.memory_id,
                content=record.content,
                category=record.category,
                score=round(score, 4),
            )
            for record, score in hits
        ]
    )


@app.post(
    "/v1/knowledge", response_model=AddKnowledgeResponse, summary="Add knowledge base"
)
def add_knowledge(req: AddKnowledgeRequest):
    """Ingest a named knowledge base of document chunks into the vector store."""
    kb_id = _memory.add_knowledge(
        name=req.name,
        chunks=[c.model_dump() for c in req.chunks],
        user_id=req.user_id,
        agent_id=req.agent_id,
        app_id=req.app_id,
        workspace_id=req.workspace_id,
    )
    return AddKnowledgeResponse(kb_id=kb_id, chunks_stored=len(req.chunks))


@app.post(
    "/v1/knowledge/search",
    response_model=KnowledgeSearchResponse,
    summary="Search knowledge",
)
def search_knowledge(req: KnowledgeSearchRequest):
    """Search knowledge base chunks by semantic similarity."""
    chunks = _memory.search_knowledge(
        req.query,
        user_id=req.user_id,
        agent_id=req.agent_id,
        app_id=req.app_id,
        workspace_id=req.workspace_id,
        top_k=req.top_k,
    )
    return KnowledgeSearchResponse(
        chunks=[
            KnowledgeChunkResult(
                chunk_id=c.chunk_id,
                kb_id=c.kb_id,
                content=c.content,
                score=round(c.score, 4),
            )
            for c in chunks
        ]
    )


@app.delete(
    "/v1/knowledge/{kb_id}",
    response_model=DeleteKnowledgeResponse,
    summary="Delete knowledge base",
)
def delete_knowledge(kb_id: str):
    """Delete a knowledge base and all its chunks by kb_id."""
    _memory.delete_knowledge(kb_id=kb_id)
    return DeleteKnowledgeResponse(deleted=True)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", summary="Health check")
def health():
    return JSONResponse({"status": "ok"})
