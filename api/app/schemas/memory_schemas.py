from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StoreMemoryRequest(BaseModel):
    agent_id: str = Field(..., description="Agent identifier")
    user_id: str = Field(..., description="User/customer identifier")
    user_message: str = Field(..., description="The user's message")
    assistant_message: Optional[str] = Field(
        None, description="The assistant's response (optional)"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for grouping"
    )
    metadata: Optional[dict] = Field(None, description="Optional metadata to attach")


class StoreMemoryResponse(BaseModel):
    success: bool
    memory_id: str
    message: str = "Memory stored successfully"


class MemoryHistoryRequest(BaseModel):
    agent_id: str
    user_id: str
    limit: int = Field(20, ge=1, le=100)
    session_id: Optional[str] = None


class MemoryTurn(BaseModel):
    id: str
    memory: str
    topics: list[str] = []
    user_id: str
    timestamp: Optional[datetime] = None


class MemoryHistoryResponse(BaseModel):
    agent_id: str
    user_id: str
    memories: list[MemoryTurn]
    total: int


class MemorySearchRequest(BaseModel):
    agent_id: str
    user_id: Optional[str] = None
    query: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=50)


class MemorySearchResult(BaseModel):
    id: str
    memory: str
    topics: list[str] = []
    user_id: str
    timestamp: Optional[datetime] = None


class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]
    total: int


class MemoryListResponse(BaseModel):
    memories: list["MemoryTurn"]
    total: int


class ClearMemoryRequest(BaseModel):
    agent_id: str
    user_id: str
    session_id: Optional[str] = None


class ClearMemoryResponse(BaseModel):
    success: bool
    deleted_count: int
    message: str
