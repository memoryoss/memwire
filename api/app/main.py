"""
MemWire API — Main Application

Self-hosted memory infrastructure for AI agents.
Provides memory storage, knowledge base, and context snapshot APIs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys

from app.config import settings
from app.db_session import ensure_agno_schema
from app.services.llm_service import initialize_llm
from app.routers import (
    memory,
    knowledge,
    api_keys,
    settings as settings_router,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting MemWire API...")

    try:
        ensure_agno_schema()
    except Exception as e:
        logger.error(f"❌ DB schema setup failed: {e}")
        sys.exit(1)

    try:
        initialize_llm()
        logger.info(f"✓ LLM provider: {settings.LLM_PROVIDER} / {settings.LLM_MODEL}")
    except Exception as e:
        logger.error(f"❌ LLM init failed: {e}")
        sys.exit(1)

    logger.info("✨ MemWire ready!")
    yield
    logger.info("👋 Shutting down MemWire...")


app = FastAPI(
    title="MemWire API",
    description="Memory infrastructure for AI agents. Store conversations, search knowledge, retrieve memories by agent.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(memory.router, prefix="/v1", tags=["memory"])
app.include_router(knowledge.router, prefix="/v1", tags=["knowledge"])
app.include_router(api_keys.router, prefix="/v1", tags=["api-keys"])
app.include_router(settings_router.router, prefix="/v1", tags=["settings"])


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
