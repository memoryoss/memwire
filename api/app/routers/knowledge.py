"""Knowledge Router — /v1/knowledge/*"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import Optional

from app.schemas.knowledge_schemas import (
    KnowledgeUploadTextRequest,
    KnowledgeUploadURLRequest,
    KnowledgeUploadResponse,
    KnowledgeListResponse,
    KnowledgeDocument,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    DeleteDocumentResponse,
)
from app.services.knowledge_service import (
    ingest_text,
    ingest_url,
    ingest_file,
    search_knowledge,
    list_documents,
    delete_document,
)
from app.utils.api_keys import require_api_key
from datetime import datetime

router = APIRouter(prefix="/knowledge")

ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "json", "csv"}


@router.post("/upload/text", response_model=KnowledgeUploadResponse)
async def upload_text(
    req: KnowledgeUploadTextRequest,
    _: dict = Depends(require_api_key),
):
    """Ingest raw text into an agent's knowledge base."""
    doc_id, chunks = ingest_text(
        agent_id=req.agent_id,
        content=req.content,
        doc_name=req.doc_name or f"text-{doc_id_preview()}",
        chunk_size=req.chunk_size,
        metadata=req.metadata,
    )
    return KnowledgeUploadResponse(
        success=True,
        doc_id=doc_id,
        doc_name=req.doc_name or doc_id,
        chunks_created=chunks,
    )


@router.post("/upload/url", response_model=KnowledgeUploadResponse)
async def upload_url(
    req: KnowledgeUploadURLRequest,
    _: dict = Depends(require_api_key),
):
    """Scrape a URL and ingest its content into the knowledge base."""
    try:
        doc_id, chunks = ingest_url(
            agent_id=req.agent_id,
            url=req.url,
            doc_name=req.doc_name,
            chunk_size=req.chunk_size,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"URL ingestion failed: {str(e)}")
    return KnowledgeUploadResponse(
        success=True,
        doc_id=doc_id,
        doc_name=req.doc_name or req.url,
        chunks_created=chunks,
    )


@router.post("/upload/file", response_model=KnowledgeUploadResponse)
async def upload_file(
    agent_id: str = Form(...),
    chunk_size: int = Form(1000),
    file: UploadFile = File(...),
    _: dict = Depends(require_api_key),
):
    """Upload a file (PDF, TXT, MD, CSV, JSON) into the knowledge base."""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    content = await file.read()
    doc_id, chunks = ingest_file(
        agent_id=agent_id,
        file_bytes=content,
        filename=file.filename,
        content_type=file.content_type or "",
        chunk_size=chunk_size,
    )
    return KnowledgeUploadResponse(
        success=True,
        doc_id=doc_id,
        doc_name=file.filename,
        chunks_created=chunks,
    )


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search(
    req: KnowledgeSearchRequest,
    _: dict = Depends(require_api_key),
):
    """Vector similarity search over the agent's knowledge base."""
    results = search_knowledge(req.agent_id, req.query, req.limit)
    return KnowledgeSearchResponse(
        results=[
            KnowledgeSearchResult(
                doc_id=r["doc_id"],
                doc_name=r["doc_name"],
                chunk=r["chunk"],
                similarity=r["similarity"],
                metadata=r.get("metadata"),
            )
            for r in results
        ],
        total=len(results),
    )


@router.get("", response_model=KnowledgeListResponse)
async def list_docs(
    agent_id: str = Query(...),
    _: dict = Depends(require_api_key),
):
    """List all documents in an agent's knowledge base."""
    docs = list_documents(agent_id)
    return KnowledgeListResponse(
        agent_id=agent_id,
        documents=[
            KnowledgeDocument(
                doc_id=d["doc_id"],
                doc_name=d["doc_name"],
                source_type=d["source_type"],
                source=d.get("source"),
                chunk_count=d.get("chunk_count", 0),
                created_at=d.get("created_at") or datetime.utcnow(),
            )
            for d in docs
        ],
        total=len(docs),
    )


@router.delete("/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_doc(
    agent_id: str = Query(...),
    doc_id: str = ...,
    _: dict = Depends(require_api_key),
):
    """Remove a document and its vectors from the knowledge base."""
    success = delete_document(agent_id, doc_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Document not found or could not be deleted"
        )
    return DeleteDocumentResponse(
        success=True, doc_id=doc_id, message="Document deleted"
    )


def doc_id_preview() -> str:
    import uuid

    return str(uuid.uuid4())[:8]
