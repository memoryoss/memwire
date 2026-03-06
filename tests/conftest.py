"""Shared fixtures for all tests."""

import os
import pytest
from memwire import MemWire, MemWireConfig

TEST_USER = "test_user"


@pytest.fixture
def config():
    """Fresh config with in-memory storage for test isolation (Qdrant-only)."""
    return MemWireConfig(
        database_url="sqlite:///:memory:",
        org_id="test_org",
        qdrant_path=":memory:",
    )


@pytest.fixture
def memory(config):
    """Fresh MemWire instance per test."""
    mem = MemWire(config=config)
    yield mem
    mem.close()


@pytest.fixture
def seeded_memory(memory):
    """Memory pre-loaded with a diverse set of memories."""
    memory.add(user_id=TEST_USER, messages=[
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
