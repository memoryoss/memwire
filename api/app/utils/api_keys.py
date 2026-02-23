"""
API Key Authentication Middleware

Validates Bearer tokens against hashed keys in memwire.api_keys.
The MEMWIRE_BOOTSTRAP_KEY env var is accepted as a master key during first setup.
"""

import hashlib
import os
import logging
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text

from app.db_session import SessionLocal

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# Bootstrap master key (set via env for first-time setup — create a real key then rotate)
BOOTSTRAP_KEY = os.getenv("MEMWIRE_BOOTSTRAP_KEY", "")


def require_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """FastAPI dependency. Validates Bearer API key. Returns key metadata dict."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    raw_key = credentials.credentials

    # Allow bootstrap key for initial setup
    if BOOTSTRAP_KEY and raw_key == BOOTSTRAP_KEY:
        return {"id": "bootstrap", "name": "bootstrap"}

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    with SessionLocal() as db:
        try:
            row = db.execute(
                text("SELECT id, name FROM memwire.api_keys WHERE key_hash = :hash"),
                {"hash": key_hash},
            ).fetchone()

            if row:
                # Update last_used_at asynchronously (best-effort)
                try:
                    db.execute(
                        text(
                            "UPDATE memwire.api_keys SET last_used_at = NOW() WHERE id = :id"
                        ),
                        {"id": row[0]},
                    )
                    db.commit()
                except Exception:
                    pass
                return {"id": row[0], "name": row[1]}
        except Exception as e:
            logger.warning(f"API key lookup failed: {e}")

    raise HTTPException(status_code=401, detail="Invalid or missing API key")
