from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class KnowledgeUploadTextRequest(BaseModel):
    agent_id: str
    content: str = Field(..., min_length=1)
    doc_name: Optional[str] = Field(None, description="Optional name for this document")
    chunk_size: int = Field(1000, ge=100, le=5000)
    metadata: Optional[dict] = None


class KnowledgeUploadURLRequest(BaseModel):
    agent_id: str
    url: str = Field(..., description="URL to scrape and ingest")
    doc_name: Optional[str] = None
    chunk_size: int = Field(1000, ge=100, le=5000)


class KnowledgeUploadResponse(BaseModel):
    success: bool
    doc_id: str
    doc_name: str
    chunks_created: int
    message: str = "Document ingested successfully"


class KnowledgeDocument(BaseModel):
    doc_id: str
    doc_name: str
    source_type: str  # file | url | text
    source: Optional[str]
    chunk_count: int
    created_at: datetime


class KnowledgeListResponse(BaseModel):
    agent_id: str
    documents: list[KnowledgeDocument]
    total: int


class KnowledgeSearchRequest(BaseModel):
    agent_id: str
    query: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    doc_id: str
    doc_name: str
    chunk: str
    similarity: float
    metadata: Optional[dict]


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeSearchResult]
    total: int


class DeleteDocumentResponse(BaseModel):
    success: bool
    doc_id: str
    message: str
