"""
Settings schemas for GET/PUT /v1/settings
"""

from pydantic import BaseModel
from typing import Optional


# ── Request bodies (allow writing sensitive fields) ────────────────────────


class LLMConfigIn(BaseModel):
    provider: str  # openai | azure_openai | anthropic | ollama | custom
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    azure_deployment: Optional[str] = None
    azure_api_version: Optional[str] = None
    # Ollama embed model (separate from chat model)
    embed_model: Optional[str] = None


class EmbedderConfigIn(BaseModel):
    provider: str  # openai | azure_openai | ollama
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    azure_deployment: Optional[str] = None
    azure_api_version: Optional[str] = None
    dimensions: int = 1536


class DatabaseConfigIn(BaseModel):
    use_bundled: bool = True
    host: Optional[str] = None
    port: int = 5432
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class SettingsUpdate(BaseModel):
    llm: Optional[LLMConfigIn] = None
    embedder: Optional[EmbedderConfigIn] = None
    database: Optional[DatabaseConfigIn] = None


# ── Response bodies (sensitive fields are masked) ──────────────────────────


class LLMConfigOut(BaseModel):
    provider: str
    model: str
    api_key_set: bool
    base_url: Optional[str] = None
    azure_deployment: Optional[str] = None
    azure_api_version: Optional[str] = None


class EmbedderConfigOut(BaseModel):
    provider: str
    model: str
    api_key_set: bool
    base_url: Optional[str] = None
    dimensions: int = 1536


class DatabaseConfigOut(BaseModel):
    use_bundled: bool
    host: Optional[str] = None
    port: int = 5432
    database: Optional[str] = None
    username: Optional[str] = None


class SettingsResponse(BaseModel):
    llm: LLMConfigOut
    embedder: EmbedderConfigOut
    database: DatabaseConfigOut
