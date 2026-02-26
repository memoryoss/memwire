"""Shared fixtures for all tests."""

import os
import pytest
from memwire import MemWire, MemWireConfig


@pytest.fixture
def config():
    """Fresh config with in-memory storage for test isolation (Qdrant-only)."""
    return MemWireConfig(
        database_url="sqlite:///:memory:",
        user_id="test_user",
        qdrant_path=":memory:",
    )


@pytest.fixture
def memory(config):
    """Fresh MemWire instance per test."""
    mem = MemWire(user_id="test_user", config=config)
    yield mem
    mem.close()


@pytest.fixture
def seeded_memory(memory):
    """Memory pre-loaded with a diverse set of memories."""
    memory.add([
        {"role": "user", "content": "We prefer organic materials for all products"},
        {"role": "assistant", "content": "Noted, I will prioritize organic suppliers"},
        {"role": "user", "content": "Our budget is limited to 50k per quarter"},
        {"role": "user", "content": "John is our main point of contact at Vendor A"},
        {"role": "user", "content": "The deadline for the project is March 15th"},
        {"role": "user", "content": "Always send reports in PDF format"},
    ])
    return memory


def cleanup_db(path):
    """Remove test database file if it exists."""
    if os.path.exists(path):
        os.remove(path)
