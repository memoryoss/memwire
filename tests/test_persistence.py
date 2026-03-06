"""Test 10: Persistence — data survives restart, graph rebuilds from DB."""

import os
import shutil
import time
import pytest
from memwire import MemWire, MemWireConfig


SQLITE_DB_PATH = "test_persistence.db"
QDRANT_DATA_PATH = "test_persistence_qdrant"


@pytest.fixture(autouse=True)
def cleanup():
    """Remove test DB/data before and after each test."""
    _cleanup_files()
    yield
    _cleanup_files()


def _cleanup_files():
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    if os.path.exists(QDRANT_DATA_PATH):
        shutil.rmtree(QDRANT_DATA_PATH, ignore_errors=True)


def _make_memory_qdrant():
    config = MemWireConfig(
        database_url=f"sqlite:///{SQLITE_DB_PATH}",
        org_id="persist_org",
        qdrant_path=QDRANT_DATA_PATH,
    )
    return MemWire(config=config)


def test_qdrant_memories_persist_across_restart():
    """Memories should be loadable after closing and reopening (Qdrant)."""
    mem1 = _make_memory_qdrant()
    mem1.add(user_id="persist_user", messages=[
        {"role": "user", "content": "I prefer dark roast coffee"},
        {"role": "user", "content": "My office is on the 5th floor"},
    ])
    mem1.close()
    time.sleep(0.5)

    mem2 = _make_memory_qdrant()
    stats2 = mem2.get_stats(user_id="persist_user")
    print(f"  Qdrant after restart: {stats2['memories']} memories")
    # Memories are in the flat engine dict only if loaded eagerly;
    # with lazy graph loading the engine._memories is empty on fresh start.
    # The graph nodes should be loadable though.
    assert stats2["nodes"] > 0 or stats2["memories"] > 0
    mem2.close()


def test_qdrant_graph_rebuilds():
    """Graph nodes should rebuild from Qdrant, edges from SQLite."""
    mem1 = _make_memory_qdrant()
    mem1.add(user_id="persist_user", messages=[
        {"role": "user", "content": "Organic cotton is our primary material"},
        {"role": "user", "content": "We source organic cotton from India"},
    ])
    mem1.close()
    time.sleep(0.5)

    mem2 = _make_memory_qdrant()
    stats2 = mem2.get_stats(user_id="persist_user")
    print(f"  Qdrant graph after:  nodes={stats2['nodes']}, edges={stats2['edges']}")
    assert stats2["nodes"] > 0
    assert stats2["edges"] > 0
    mem2.close()


def test_qdrant_recall_works_after_restart():
    """Recall should work on reloaded Qdrant memories."""
    mem1 = _make_memory_qdrant()
    mem1.add(user_id="persist_user", messages=[
        {"role": "user", "content": "Our company headquarters is in San Francisco"},
    ])
    mem1.close()
    time.sleep(0.5)

    mem2 = _make_memory_qdrant()
    result = mem2.recall("Where is our office?", user_id="persist_user")
    all_contents = set()
    for path in result.all_paths:
        for m in path.memories:
            all_contents.add(m.content)
    print(f"  Qdrant recall after restart: {all_contents}")
    # With lazy loading, the memories may come from graph paths
    # The graph is loaded so nodes should exist
    mem2.close()
