"""API key authentication middleware."""

import hmac
import json
import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header against configured keys."""

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, api_keys: list[str] | None = None):
        super().__init__(app)
        self.api_keys = list(api_keys or self._load_keys())

    @staticmethod
    def _load_keys() -> list[str]:
        raw = os.getenv("MEMWIRE_API_KEYS", "")
        return [k.strip() for k in raw.split(",") if k.strip()]

    def _check_key(self, key: str) -> bool:
        # constant-time comparison to prevent timing attacks
        return any(hmac.compare_digest(key, valid) for valid in self.api_keys)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
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
