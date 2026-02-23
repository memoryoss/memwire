"""
Settings Router — GET/PUT /v1/settings

Allows reading and updating LLM, Embedder, and Database configuration
at runtime. Changes are applied immediately (LLM is reinitialized) and
persisted to the .env file for survival across container restarts.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.services.llm_service import reinitialize_llm
from app.utils.api_keys import require_api_key
from app.schemas.settings_schemas import (
    SettingsUpdate,
    SettingsResponse,
    LLMConfigOut,
    EmbedderConfigOut,
    DatabaseConfigOut,
)

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)

ENV_FILE = Path("/api/.env")


# ── Helpers ────────────────────────────────────────────────────────────────

def _mask(key: Optional[str]) -> bool:
    """Return True if the key has a non-empty value."""
    return bool(key and key.strip())


def _parse_db_url(url: str):
    """
    Parse a postgres URL like:
    postgresql://user:password@host:5432/database
    Returns (host, port, database, username) — password is never returned.
    """
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        return {
            "host": p.hostname,
            "port": p.port or 5432,
            "database": p.path.lstrip("/"),
            "username": p.username,
        }
    except Exception:
        return {}


def _write_env(updates: dict):
    """
    Write/update key=value pairs in /api/.env.
    Keys not present are appended. Existing keys are updated in place.
    """
    try:
        lines: list[str] = []
        if ENV_FILE.exists():
            lines = ENV_FILE.read_text().splitlines()

        existing_keys = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0]
                existing_keys[k] = i

        for key, value in updates.items():
            if value is None:
                continue
            entry = f"{key}={value}"
            if key in existing_keys:
                lines[existing_keys[key]] = entry
            else:
                lines.append(entry)

        ENV_FILE.write_text("\n".join(lines) + "\n")
        logger.info(f"✓ .env updated: {list(updates.keys())}")
    except Exception as e:
        logger.warning(f"Could not write .env: {e}")


# ── GET /v1/settings ────────────────────────────────────────────────────────

@router.get("", response_model=SettingsResponse)
async def get_settings(_=Depends(require_api_key)):
    db_parsed = {}
    if not settings.USE_BUNDLED_DB:
        db_parsed = _parse_db_url(settings.DATABASE_URL)

    return SettingsResponse(
        llm=LLMConfigOut(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            api_key_set=_mask(settings.LLM_API_KEY),
            base_url=settings.LLM_BASE_URL or None,
            azure_deployment=settings.LLM_MODEL if settings.LLM_PROVIDER == "azure_openai" else None,
            azure_api_version=settings.AZURE_API_VERSION or None,
        ),
        embedder=EmbedderConfigOut(
            provider=settings.LLM_PROVIDER,  # embedder uses same provider
            model=settings.EMBEDDING_MODEL,
            api_key_set=_mask(settings.LLM_API_KEY),
            base_url=settings.LLM_BASE_URL or None,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        ),
        database=DatabaseConfigOut(
            use_bundled=settings.USE_BUNDLED_DB,
            **db_parsed,
        ),
    )


# ── PUT /v1/settings ────────────────────────────────────────────────────────

@router.put("", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate, _=Depends(require_api_key)):
    env_updates: dict = {}
    llm_changed = False

    # ── LLM update ──────────────────────────────────────────────────────────
    if body.llm:
        llm = body.llm
        settings.LLM_PROVIDER = llm.provider
        env_updates["LLM_PROVIDER"] = llm.provider

        settings.LLM_MODEL = llm.model
        env_updates["LLM_MODEL"] = llm.model

        if llm.api_key:
            settings.LLM_API_KEY = llm.api_key
            env_updates["LLM_API_KEY"] = llm.api_key

        if llm.base_url is not None:
            settings.LLM_BASE_URL = llm.base_url
            env_updates["LLM_BASE_URL"] = llm.base_url

        if llm.azure_api_version:
            settings.AZURE_API_VERSION = llm.azure_api_version
            env_updates["AZURE_API_VERSION"] = llm.azure_api_version

        llm_changed = True

    # ── Embedder update ─────────────────────────────────────────────────────
    if body.embedder:
        emb = body.embedder
        settings.EMBEDDING_MODEL = emb.model
        env_updates["EMBEDDING_MODEL"] = emb.model

        if emb.dimensions:
            settings.EMBEDDING_DIMENSIONS = emb.dimensions
            env_updates["EMBEDDING_DIMENSIONS"] = str(emb.dimensions)

        # embedder api_key/base_url updates the same LLM_* settings
        if emb.api_key:
            settings.LLM_API_KEY = emb.api_key
            env_updates["LLM_API_KEY"] = emb.api_key

        if emb.base_url is not None:
            settings.LLM_BASE_URL = emb.base_url
            env_updates["LLM_BASE_URL"] = emb.base_url

        llm_changed = True

    # ── Database update ─────────────────────────────────────────────────────
    if body.database:
        db = body.database
        settings.USE_BUNDLED_DB = db.use_bundled
        env_updates["USE_BUNDLED_DB"] = str(db.use_bundled).lower()

        if not db.use_bundled and all(
            [db.host, db.database, db.username, db.password]
        ):
            port = db.port or 5432
            url = f"postgresql://{db.username}:{db.password}@{db.host}:{port}/{db.database}"
            settings.DATABASE_URL = url
            env_updates["DATABASE_URL"] = url

    # ── Write .env and reinitialize LLM ─────────────────────────────────────
    if env_updates:
        _write_env(env_updates)

    if llm_changed:
        try:
            reinitialize_llm()
            logger.info("✓ LLM reinitialized after settings update")
        except Exception as e:
            logger.error(f"LLM reinit failed: {e}")
            raise HTTPException(status_code=422, detail=f"Settings saved but LLM init failed: {e}")

    return await get_settings(_)
