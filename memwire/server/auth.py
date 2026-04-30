"""API key authentication middleware."""

import hmac
import json
import logging
import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header against configured keys."""

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
    EXEMPT_PREFIXES = ("/studio",)

    def __init__(self, app, api_keys: list[str] | None = None):
        super().__init__(app)
        self.api_keys = list(api_keys or self._load_keys())
        if not self.api_keys:
            logger.warning(
                "================================================================\n"
                "  MEMWIRE_API_KEYS is empty — API authentication is DISABLED.\n"
                "  Anyone with network access to this server can read or write\n"
                "  every memory and knowledge base. Safe for localhost only.\n"
                "  Set MEMWIRE_API_KEYS=<secret> in your .env before exposing\n"
                "  this beyond 127.0.0.1.\n"
                "================================================================"
            )

    @staticmethod
    def _load_keys() -> list[str]:
        raw = os.getenv("MEMWIRE_API_KEYS", "")
        return [k.strip() for k in raw.split(",") if k.strip()]

    def _check_key(self, key: str) -> bool:
        return any(hmac.compare_digest(key, valid) for valid in self.api_keys)

    def _is_exempt(self, path: str) -> bool:
        if path in self.EXEMPT_PATHS:
            return True
        for prefix in self.EXEMPT_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        if self._is_exempt(request.url.path):
            return await call_next(request)

        if not self.api_keys:
            return await call_next(request)

        key = request.headers.get("X-API-Key")
        if not key or not self._check_key(key):
            return Response(
                content=json.dumps({"detail": "Invalid or missing API key"}),
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
