from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import json
import os


class Settings(BaseSettings):
    # Application
    APP_ENV: str = "production"
    LOG_LEVEL: str = "info"

    # LLM Provider
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = ""
    AZURE_API_VERSION: str = "2024-02-15-preview"

    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Database
    USE_BUNDLED_DB: bool = True
    DATABASE_URL: str = "postgresql://memwire:memwire@db:5432/memwire"

    # Security
    API_SECRET_KEY: str = "change-me"
    MEMWIRE_BOOTSTRAP_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Memory
    DEFAULT_HISTORY_TURNS: int = 20
    DEFAULT_MAX_CONTEXT_TOKENS: int = 2000
    DATA_RETENTION_DAYS: int = 90

    # Knowledge
    MAX_KNOWLEDGE_BASES: int = 20
    KB_CHUNK_SIZE: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
