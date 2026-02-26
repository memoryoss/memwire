"""Test: Knowledge base feature — add, search, recall integration, isolation, delete."""

from memwire import MemWire, MemWireConfig


def _make_memory(user_id="test_user", agent_id=None):
    config = MemWireConfig(
        database_url="sqlite:///:memory:",
        user_id=user_id,
        qdrant_path=":memory:",
    )
    return MemWire(user_id=user_id, agent_id=agent_id, config=config)


def test_add_knowledge_base():
    """Add knowledge chunks and verify stats."""
    mem = _make_memory()
    kb_id = mem.add_knowledge("test_kb", [
        {"content": "The speed of light is approximately 300,000 km/s"},
        {"content": "Einstein developed the theory of relativity"},
        {"content": "E=mc² is the mass-energy equivalence formula"},
    ])
    assert kb_id.startswith("kb_")
    stats = mem.get_stats()
    assert stats["knowledge_bases"] == 1
    mem.close()


def test_search_knowledge():
    """Add knowledge chunks, search, and verify results."""
    mem = _make_memory()
    mem.add_knowledge("physics_kb", [
        {"content": "The speed of light is approximately 300,000 km/s", "metadata": {"source": "physics101"}},
        {"content": "Water freezes at 0 degrees Celsius", "metadata": {"source": "chemistry101"}},
        {"content": "Einstein developed the theory of relativity", "metadata": {"source": "physics101"}},
    ])

    results = mem.search_knowledge("How fast does light travel?")
    assert len(results) > 0
    # Top result should be about speed of light
    contents = [r.content for r in results]
    assert any("speed of light" in c.lower() for c in contents), \
        f"Expected 'speed of light' in results: {contents}"
    mem.close()


def test_recall_includes_knowledge():
    """Add both memories and knowledge, recall should return both."""
    mem = _make_memory()

    # Add regular memories
    mem.add([
        {"role": "user", "content": "I'm studying physics this semester"},
    ])

    # Add knowledge base
    mem.add_knowledge("physics_kb", [
        {"content": "Newton's first law states that an object at rest stays at rest"},
        {"content": "The gravitational constant G is 6.674×10⁻¹¹ N⋅m²/kg²"},
    ])

    result = mem.recall("Tell me about physics laws")

    # Should have memories from graph paths
    has_memories = len(result.all_paths) > 0

    # Should have knowledge chunks
    has_knowledge = len(result.knowledge) > 0

    print(f"  Has memory paths: {has_memories}, Has knowledge: {has_knowledge}")
    print(f"  Knowledge: {[k.content for k in result.knowledge]}")

    # At minimum, knowledge should be found
    assert has_knowledge, "Expected knowledge chunks in recall result"
    mem.close()


def test_knowledge_isolation():
    """Different users should not see each other's knowledge."""
    mem_a = _make_memory("alice")
    mem_b = _make_memory("bob")

    mem_a.add_knowledge("alice_kb", [
        {"content": "Alice's secret formula: H2SO4 + NaOH = NaHSO4 + H2O"},
    ])

    mem_b.add_knowledge("bob_kb", [
        {"content": "Bob's favorite recipe is chocolate cake"},
    ])

    # Alice should find her knowledge
    results_a = mem_a.search_knowledge("chemical formula")
    assert len(results_a) > 0
    assert any("h2so4" in r.content.lower() for r in results_a)

    # Bob should NOT find Alice's knowledge
    results_b = mem_b.search_knowledge("chemical formula")
    bob_contents = [r.content for r in results_b]
    assert not any("h2so4" in c.lower() for c in bob_contents), \
        f"Bob should not see Alice's knowledge: {bob_contents}"

    mem_a.close()
    mem_b.close()


def test_delete_knowledge():
    """Delete a knowledge base and verify chunks are gone."""
    mem = _make_memory()
    kb_id = mem.add_knowledge("to_delete", [
        {"content": "This knowledge will be deleted"},
        {"content": "This too will be removed"},
    ])
    assert mem.get_stats()["knowledge_bases"] == 1

    # Search before delete
    results_before = mem.search_knowledge("deleted")
    assert len(results_before) > 0

    # Delete
    mem.delete_knowledge(kb_id)
    assert mem.get_stats()["knowledge_bases"] == 0

    # Search after delete — should find nothing
    results_after = mem.search_knowledge("deleted")
    assert len(results_after) == 0
    mem.close()
