"""MemWire REST API server."""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware

from memwire import MemWire, MemWireConfig
from .auth import APIKeyMiddleware
from .config_store import LLMConfigStore
from .llm import LLMClient, LLMConfig
from .routes import memories, knowledge, health, stats, chat, llm

logger = logging.getLogger(__name__)


class StudioStaticFiles(StaticFiles):
    """StaticFiles that falls back to index.html for SPA client-side routing."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as ex:
            if ex.status_code == 404:
                try:
                    return await super().get_response("index.html", scope)
                except StarletteHTTPException:
                    pass
            raise


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

    app.state.llm_store = LLMConfigStore()
    env_llm_config = LLMConfig.from_env()
    if env_llm_config is not None:
        app.state.llm = LLMClient(env_llm_config)
        app.state.llm_locked = True
        logger.info(
            "LLM provider configured via env: base_url=%s default_model=%s (UI is read-only)",
            env_llm_config.base_url, env_llm_config.default_model,
        )
    else:
        app.state.llm_locked = False
        stored = app.state.llm_store.load()
        if stored and stored.get("api_key"):
            base_url = (stored.get("base_url") or "https://api.openai.com/v1").rstrip("/")
            default_model = stored.get("default_model") or "gpt-4o-mini"
            models = stored.get("available_models") or [default_model]
            ui_config = LLMConfig(
                api_key=stored["api_key"],
                base_url=base_url,
                default_model=default_model,
                available_models=[m for m in models if m] or [default_model],
            )
            app.state.llm = LLMClient(ui_config)
            logger.info(
                "LLM provider loaded from saved config: base_url=%s default_model=%s",
                ui_config.base_url, ui_config.default_model,
            )
        else:
            app.state.llm = None
            logger.info("LLM provider not configured — /v1/chat will return 503 until set via UI or env")

    logger.info("MemWire ready")
    yield
    logger.info("Shutting down MemWire...")
    app.state.memory.close()
    if getattr(app.state, "llm", None) is not None:
        await app.state.llm.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MemWire API",
        description="Memory infrastructure for AI agents",
        version="0.3.0",
        lifespan=lifespan,
    )

    cors_origins = os.getenv("MEMWIRE_CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(APIKeyMiddleware)

    app.include_router(memories.router)
    app.include_router(knowledge.router)
    app.include_router(stats.router)
    app.include_router(chat.router)
    app.include_router(llm.router)
    app.include_router(health.router)

    studio_dir = os.getenv("STUDIO_STATIC_DIR", "/app/studio-static")
    if os.path.isdir(studio_dir):
        app.mount(
            "/studio",
            StudioStaticFiles(directory=studio_dir, html=True),
            name="studio",
        )
        logger.info("Studio mounted at /studio from %s", studio_dir)
    else:
        logger.info("Studio static dir not found at %s — skipping mount", studio_dir)

    return app


app = create_app()
