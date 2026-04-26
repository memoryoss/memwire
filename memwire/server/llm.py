"""LLM provider configuration + thin async HTTP client.

Memwire's chat endpoint proxies to any OpenAI-compatible /chat/completions
endpoint. Configuration is read from environment variables on app startup:

    OPENAI_API_KEY          (required to enable /v1/chat)
    OPENAI_BASE_URL         (default: https://api.openai.com/v1)
    OPENAI_DEFAULT_MODEL    (default: gpt-4o-mini)
    OPENAI_AVAILABLE_MODELS (comma-separated, optional)
"""

import os
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class LLMConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o-mini"
    available_models: list[str] = field(default_factory=lambda: ["gpt-4o-mini", "gpt-4o"])
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> Optional["LLMConfig"]:
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            return None
        models_raw = os.getenv("OPENAI_AVAILABLE_MODELS", "").strip()
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
        default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini").strip()
        if not models:
            models = [default_model]
        return cls(
            api_key=key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            default_model=default_model,
            available_models=models,
        )


class LLMClient:
    """Async OpenAI-compatible chat client."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=config.timeout_seconds)

    async def chat(self, messages: list[dict], model: Optional[str] = None) -> dict:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model or self.config.default_model,
            "messages": messages,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        resp = await self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
