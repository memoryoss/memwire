"""LLM provider config endpoints — UI fallback when OPENAI_API_KEY is empty.

Behaviour:
    - GET    /v1/llm/config  — current state (masked api key + lock status)
    - POST   /v1/llm/config  — write new config + hot-swap LLMClient (423 if locked)
    - DELETE /v1/llm/config  — wipe stored config + close client (423 if locked)
    - POST   /v1/llm/test    — probe a config (provided body or current state)

When the backend was started with ``OPENAI_API_KEY`` set, ``env_locked`` is
true and POST/DELETE return 423.
"""

import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request

from ..llm import LLMClient, LLMConfig
from ..schemas import (
    LLMConfigItem,
    LLMConfigResponse,
    LLMTestRequest,
    LLMTestResponse,
)

router = APIRouter(prefix="/v1/llm", tags=["llm"])


def _mask(key: str) -> tuple[Optional[str], Optional[str]]:
    if not key:
        return None, None
    if len(key) <= 8:
        return key[:4], None
    return key[:4], key[-4:]


def _state(client: Optional[LLMClient], locked: bool) -> LLMConfigResponse:
    if client is None:
        return LLMConfigResponse(
            configured=False,
            env_locked=locked,
            base_url="",
            default_model="",
            available_models=[],
        )
    prefix, suffix = _mask(client.config.api_key)
    return LLMConfigResponse(
        configured=True,
        env_locked=locked,
        base_url=client.config.base_url,
        default_model=client.config.default_model,
        available_models=client.config.available_models,
        api_key_prefix=prefix,
        api_key_suffix=suffix,
    )


@router.get("/config", response_model=LLMConfigResponse)
def get_config(request: Request):
    return _state(
        getattr(request.app.state, "llm", None),
        getattr(request.app.state, "llm_locked", False),
    )


@router.post("/config", response_model=LLMConfigResponse)
async def save_config(body: LLMConfigItem, request: Request):
    if getattr(request.app.state, "llm_locked", False):
        raise HTTPException(
            status_code=423,
            detail=(
                "LLM is configured via the OPENAI_API_KEY env var; UI edits "
                "are disabled. Unset that env var and restart to manage from "
                "the UI."
            ),
        )
    api_key = (body.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    base_url = (body.base_url or "https://api.openai.com/v1").rstrip("/")
    default_model = (body.default_model or "gpt-4o-mini").strip()
    models = body.available_models or [default_model]
    models = [m.strip() for m in models if m and m.strip()] or [default_model]

    new_config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        available_models=models,
    )

    request.app.state.llm_store.save({
        "api_key": new_config.api_key,
        "base_url": new_config.base_url,
        "default_model": new_config.default_model,
        "available_models": new_config.available_models,
    })

    old = getattr(request.app.state, "llm", None)
    if old is not None:
        await old.close()
    request.app.state.llm = LLMClient(new_config)
    return _state(request.app.state.llm, locked=False)


@router.delete("/config", response_model=LLMConfigResponse)
async def clear_config(request: Request):
    if getattr(request.app.state, "llm_locked", False):
        raise HTTPException(
            status_code=423,
            detail="Cannot clear UI config while OPENAI_API_KEY env var is set.",
        )
    request.app.state.llm_store.clear()
    old = getattr(request.app.state, "llm", None)
    if old is not None:
        await old.close()
    request.app.state.llm = None
    return _state(None, locked=False)


@router.post("/test", response_model=LLMTestResponse)
async def test_llm(body: LLMTestRequest, request: Request):
    """Probe the LLM provider with a one-token prompt.

    If ``body.api_key`` is provided, the request tests that ad-hoc config
    (without saving). Otherwise it tests the currently-active config.
    """
    use_temp = bool(body.api_key and body.api_key.strip())
    if use_temp:
        default_model = (body.default_model or "gpt-4o-mini").strip()
        cfg = LLMConfig(
            api_key=body.api_key.strip(),
            base_url=(body.base_url or "https://api.openai.com/v1").rstrip("/"),
            default_model=default_model,
            available_models=[default_model],
        )
        client = LLMClient(cfg)
    else:
        client = getattr(request.app.state, "llm", None)
        if client is None:
            return LLMTestResponse(ok=False, error="No LLM provider configured")

    start = time.time()
    try:
        result = await client.chat(
            [{"role": "user", "content": "Reply with the single word: ok"}],
            model=client.config.default_model,
        )
        latency_ms = round((time.time() - start) * 1000, 1)
        return LLMTestResponse(
            ok=True,
            model=result.get("model", client.config.default_model),
            latency_ms=latency_ms,
        )
    except httpx.HTTPStatusError as e:
        body_text = (e.response.text or "")[:240]
        return LLMTestResponse(
            ok=False,
            error=f"HTTP {e.response.status_code}: {body_text or e.response.reason_phrase}",
        )
    except httpx.RequestError as e:
        return LLMTestResponse(ok=False, error=f"Connection failed: {e}")
    except Exception as e:  # noqa: BLE001 — surface to UI verbatim
        return LLMTestResponse(ok=False, error=str(e))
    finally:
        if use_temp:
            await client.close()
