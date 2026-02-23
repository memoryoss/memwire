"""API Keys Router — /v1/api-keys/*"""

import uuid
import secrets
import hashlib
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.schemas.agent_schemas import (
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    APIKeyResponse,
    APIKeyListResponse,
    DeleteAPIKeyResponse,
)
from app.db_session import SessionLocal
from app.utils.api_keys import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-keys")

KEY_PREFIX = "mw_"


def _ensure_keys_table(db):
    db.execute(
        text(
            """
            CREATE SCHEMA IF NOT EXISTS memwire;
            CREATE TABLE IF NOT EXISTS memwire.api_keys (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT,
                key_hash    TEXT NOT NULL UNIQUE,
                key_prefix  TEXT NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                last_used_at TIMESTAMPTZ
            )
            """
        )
    )


@router.get("", response_model=APIKeyListResponse)
async def list_keys(_: dict = Depends(require_api_key)):
    with SessionLocal() as db:
        try:
            rows = db.execute(
                text(
                    "SELECT id, name, description, key_prefix, created_at, last_used_at FROM memwire.api_keys ORDER BY created_at DESC"
                )
            ).fetchall()
        except Exception:
            _ensure_keys_table(db)
            db.commit()
            rows = []
    return APIKeyListResponse(
        keys=[
            APIKeyResponse(
                id=r[0],
                name=r[1],
                description=r[2],
                key_prefix=r[3],
                created_at=r[4],
                last_used_at=r[5],
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.post("", response_model=CreateAPIKeyResponse, status_code=201)
async def create_key(req: CreateAPIKeyRequest, _: dict = Depends(require_api_key)):
    raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12] + "..."
    key_id = str(uuid.uuid4())
    now = datetime.utcnow()

    with SessionLocal() as db:
        try:
            _ensure_keys_table(db)
            db.execute(
                text(
                    """
                    INSERT INTO memwire.api_keys (id, name, description, key_hash, key_prefix, created_at)
                    VALUES (:id, :name, :desc, :hash, :prefix, :now)
                    """
                ),
                {
                    "id": key_id,
                    "name": req.name,
                    "desc": req.description,
                    "hash": key_hash,
                    "prefix": key_prefix,
                    "now": now,
                },
            )
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    return CreateAPIKeyResponse(
        id=key_id,
        name=req.name,
        key=raw_key,
        key_prefix=key_prefix,
        created_at=now,
    )


@router.delete("/{key_id}", response_model=DeleteAPIKeyResponse)
async def delete_key(key_id: str, _: dict = Depends(require_api_key)):
    with SessionLocal() as db:
        result = db.execute(
            text("DELETE FROM memwire.api_keys WHERE id = :id"), {"id": key_id}
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="API key not found")
    return DeleteAPIKeyResponse(success=True, key_id=key_id)
