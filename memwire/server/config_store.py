"""Persistent LLM config that lives outside env vars.

Used as a fallback when ``OPENAI_API_KEY`` is unset. The Studio UI can write
to it; on write, the running ``LLMClient`` is rebuilt without a restart.

Stored as JSON at ``{config_dir}/llm_config.json`` with file mode ``0600``.
The api_key sits in plaintext — no worse than the SQLite DB on the same
volume. If you want stricter handling, set ``OPENAI_API_KEY`` in the
environment instead and the store stays empty.
"""

import json
import os
from pathlib import Path
from typing import Optional


CONFIG_FILE = "llm_config.json"


def get_config_dir() -> Path:
    """Resolve the directory where ``llm_config.json`` lives.

    Precedence:
        1. ``MEMWIRE_CONFIG_DIR`` env override
        2. ``/data`` if it exists and is writable (the Docker volume)
        3. ``./memwire_config`` (dev fallback, relative to cwd)
    """
    explicit = os.getenv("MEMWIRE_CONFIG_DIR", "").strip()
    if explicit:
        path = Path(explicit)
    elif Path("/data").is_dir() and os.access("/data", os.W_OK):
        path = Path("/data")
    else:
        path = Path("./memwire_config")
    path.mkdir(parents=True, exist_ok=True)
    return path


class LLMConfigStore:
    """JSON-backed LLM config persistence."""

    def __init__(self, path: Optional[Path] = None):
        directory = path if path is not None else get_config_dir()
        self.path = Path(directory) / CONFIG_FILE

    def load(self) -> Optional[dict]:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, data: dict) -> None:
        # Atomic write: temp + rename. chmod before rename so the published
        # file always has the right mode.
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.path)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
