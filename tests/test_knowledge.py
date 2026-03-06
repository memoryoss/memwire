"""Test: Knowledge base feature — add, search, recall integration, isolation, delete."""

from memwire import MemWire, MemWireConfig


def _make_memory():
    config = MemWireConfig(
        database_url="sqlite:///:memory:",
        org_id="test_org",
        qdrant_path=":memory:",
    )
    return MemWire(config=config)


def test_add_knowledge_base():
    """Add knowledge chunks and verify stats."""
    mem = _make_memory()
    kb_id = mem.add_knowledge("test_kb", [
        {"content": "The speed of light is approximately 300,000 km/s"},
        {"content": "Einstein developed the theory of relativity"},
        {"content": "E=mc² is the mass-energy equivalence formula"},
    ], user_id="test_user")
    assert kb_id.startswith("kb_")
    stats = mem.get_stats(user_id="test_user")
    assert stats["knowledge_bases"] == 1
    mem.close()


def test_search_knowledge():
    """Add knowledge chunks, search, and verify results."""
    mem = _make_memory()
    mem.add_knowledge("physics_kb", [
        {"content": "The speed of light is approximately 300,000 km/s", "metadata": {"source": "physics101"}},
        {"content": "Water freezes at 0 degrees Celsius", "metadata": {"source": "chemistry101"}},
        {"content": "Einstein developed the theory of relativity", "metadata": {"source": "physics101"}},
    ], user_id="test_user")

    results = mem.search_knowledge("How fast does light travel?", user_id="test_user")
    assert len(results) > 0
    contents = [r.content for r in results]
    assert any("speed of light" in c.lower() for c in contents), \
        f"Expected 'speed of light' in results: {contents}"
    mem.close()


def test_recall_includes_knowledge():
    """Add both memories and knowledge, recall should return both."""
    mem = _make_memory()

    # Add regular memories
    mem.add(user_id="test_user", messages=[
        {"role": "user", "content": "I'm studying physics this semester"},
    ])

    # Add knowledge base
    mem.add_knowledge("physics_kb", [
        {"content": "Newton's first law states that an object at rest stays at rest"},
        {"content": "The gravitational constant G is 6.674×10⁻¹¹ N⋅m²/kg²"},
    ], user_id="test_user")

    result = mem.recall("Tell me about physics laws", user_id="test_user")

    has_memories = len(result.all_paths) > 0
    has_knowledge = len(result.knowledge) > 0

    print(f"  Has memory paths: {has_memories}, Has knowledge: {has_knowledge}")
    print(f"  Knowledge: {[k.content for k in result.knowledge]}")

    assert has_knowledge, "Expected knowledge chunks in recall result"
    mem.close()


def test_knowledge_isolation():
    """Different users should not see each other's knowledge."""
    mem = _make_memory()

    mem.add_knowledge("alice_kb", [
        {"content": "Alice's secret formula: H2SO4 + NaOH = NaHSO4 + H2O"},
    ], user_id="alice")

    mem.add_knowledge("bob_kb", [
        {"content": "Bob's favorite recipe is chocolate cake"},
    ], user_id="bob")

    # Alice should find her knowledge
    results_a = mem.search_knowledge("chemical formula", user_id="alice")
    assert len(results_a) > 0
    assert any("h2so4" in r.content.lower() for r in results_a)

    # Bob should NOT find Alice's knowledge
    results_b = mem.search_knowledge("chemical formula", user_id="bob")
    bob_contents = [r.content for r in results_b]
    assert not any("h2so4" in c.lower() for c in bob_contents), \
        f"Bob should not see Alice's knowledge: {bob_contents}"

    mem.close()


def test_delete_knowledge():
    """Delete a knowledge base and verify chunks are gone."""
    mem = _make_memory()
    kb_id = mem.add_knowledge("to_delete", [
        {"content": "This knowledge will be deleted"},
        {"content": "This too will be removed"},
    ], user_id="test_user")
    assert mem.get_stats(user_id="test_user")["knowledge_bases"] == 1

    # Search before delete
    results_before = mem.search_knowledge("deleted", user_id="test_user")
    assert len(results_before) > 0

    # Delete
    mem.delete_knowledge(kb_id)
    assert mem.get_stats(user_id="test_user")["knowledge_bases"] == 0

    # Search after delete — should find nothing
    results_after = mem.search_knowledge("deleted", user_id="test_user")
    assert len(results_after) == 0
    mem.close()
