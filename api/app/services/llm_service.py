"""
LLM Service — Bring Your Own LLM (BYOLL)

Builds an Agno-compatible model from environment config.
Supported providers: openai, azure_openai, anthropic, ollama, custom
"""

import logging
from typing import Optional

from agno.models.openai.chat import OpenAIChat
from agno.knowledge.embedder.openai import OpenAIEmbedder

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
_embedder = None
_initialized = False


def initialize_llm():
    """Initialize the LLM model and embedder at startup."""
    global _model, _embedder, _initialized

    if _initialized:
        return

    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        _model = OpenAIChat(
            id=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
        )
        _embedder = OpenAIEmbedder(
            id=settings.EMBEDDING_MODEL,
            api_key=settings.LLM_API_KEY,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )

    elif provider == "azure_openai":
        from agno.models.azure.openai_chat import AzureOpenAI
        from agno.knowledge.embedder.azure_openai import AzureOpenAIEmbedder

        _model = AzureOpenAI(
            id=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            azure_endpoint=settings.LLM_BASE_URL,
            azure_deployment=settings.LLM_MODEL,
            api_version=settings.AZURE_API_VERSION,
        )
        _embedder = AzureOpenAIEmbedder(
            id=settings.EMBEDDING_MODEL,
            api_key=settings.LLM_API_KEY,
            azure_endpoint=settings.LLM_BASE_URL,
            azure_deployment=settings.EMBEDDING_MODEL,
            api_version=settings.AZURE_API_VERSION,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )

    elif provider == "anthropic":
        from agno.models.anthropic import Claude

        _model = Claude(
            id=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
        )
        # Anthropic doesn't have its own embedder — fall back to OpenAI
        _embedder = OpenAIEmbedder(
            id=settings.EMBEDDING_MODEL,
            api_key=settings.LLM_API_KEY,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )

    elif provider == "ollama":
        from agno.models.ollama import Ollama
        from agno.knowledge.embedder.ollama import OllamaEmbedder

        base_url = settings.LLM_BASE_URL or "http://localhost:11434"
        _model = Ollama(id=settings.LLM_MODEL, host=base_url)
        _embedder = OllamaEmbedder(
            id=settings.EMBEDDING_MODEL or "nomic-embed-text",
            host=base_url,
        )

    elif provider == "custom":
        # OpenAI-compatible endpoint
        _model = OpenAIChat(
            id=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY or "not-needed",
            base_url=settings.LLM_BASE_URL,
        )
        _embedder = OpenAIEmbedder(
            id=settings.EMBEDDING_MODEL,
            api_key=settings.LLM_API_KEY or "not-needed",
            base_url=settings.LLM_BASE_URL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    _initialized = True
    logger.info(f"✓ LLM initialized: provider={provider}, model={settings.LLM_MODEL}")


def get_model():
    """Return the initialized Agno model."""
    if not _initialized:
        initialize_llm()
    return _model


def get_embedder():
    """Return the initialized Agno embedder."""
    if not _initialized:
        initialize_llm()
    return _embedder


def reinitialize_llm():
    """Force-reinitialize the LLM and embedder (call after settings change)."""
    global _model, _embedder, _initialized
    _model = None
    _embedder = None
    _initialized = False

    # Clear agent component cache so new agents use the updated model
    try:
        from app.services.agent_service import _agent_components

        _agent_components.clear()
    except Exception:
        pass

    initialize_llm()
