"""MemWire REST API server."""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from memwire import MemWire, MemWireConfig
from .auth import APIKeyMiddleware
from .routes import memories, knowledge, health

logger = logging.getLogger(__name__)


def _build_config() -> MemWireConfig:
    """Build MemWireConfig from environment variables."""
    kwargs = {}
    if os.getenv("QDRANT_URL"):
        kwargs["qdrant_url"] = os.getenv("QDRANT_URL")
    if os.getenv("QDRANT_API_KEY"):
        kwargs["qdrant_api_key"] = os.getenv("QDRANT_API_KEY")
    if os.getenv("QDRANT_PATH"):
        kwargs["qdrant_path"] = os.getenv("QDRANT_PATH")
    if os.getenv("DATABASE_URL"):
        kwargs["database_url"] = os.getenv("DATABASE_URL")
    if os.getenv("MEMWIRE_ORG_ID"):
        kwargs["org_id"] = os.getenv("MEMWIRE_ORG_ID")
    if os.getenv("MEMWIRE_COLLECTION_PREFIX"):
        kwargs["qdrant_collection_prefix"] = os.getenv("MEMWIRE_COLLECTION_PREFIX")
    # embedding provider config
    if os.getenv("EMBEDDING_PROVIDER"):
        kwargs["embedding_provider"] = os.getenv("EMBEDDING_PROVIDER")
    if os.getenv("EMBEDDING_API_URL"):
        kwargs["embedding_api_url"] = os.getenv("EMBEDDING_API_URL")
    if os.getenv("EMBEDDING_API_KEY"):
        kwargs["embedding_api_key"] = os.getenv("EMBEDDING_API_KEY")
    if os.getenv("EMBEDDING_MODEL"):
        kwargs["embedding_model"] = os.getenv("EMBEDDING_MODEL")
    if os.getenv("EMBEDDING_DIM"):
        kwargs["embedding_dim"] = int(os.getenv("EMBEDDING_DIM"))
    return MemWireConfig(**kwargs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MemWire server...")
    config = _build_config()
    app.state.memory = MemWire(config=config)
    logger.info("MemWire ready")
    yield
    logger.info("Shutting down MemWire...")
    app.state.memory.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MemWire API",
        description="Memory infrastructure for AI agents",
        version="0.3.0",
        lifespan=lifespan,
    )

    app.add_middleware(APIKeyMiddleware)

    app.include_router(memories.router)
    app.include_router(knowledge.router)
    app.include_router(health.router)

    return app


app = create_app()
