"""Test 11: Multi-user and multi-agent isolation — single MemWire instance."""

from memwire import MemWire, MemWireConfig


def _make_shared_memory() -> MemWire:
    config = MemWireConfig(
        database_url="sqlite:///:memory:",
        org_id="test_org",
        qdrant_path=":memory:",
    )
    return MemWire(config=config)


def test_users_are_isolated():
    """User A's memories should not appear in User B's recall (same instance)."""
    mem = _make_shared_memory()

    mem.add(user_id="alice", messages=[{"role": "user", "content": "My secret code is alpha-bravo-42"}])
    mem.add(user_id="bob", messages=[{"role": "user", "content": "I enjoy hiking in the mountains"}])

    # Bob should NOT see Alice's secret
    bob_result = mem.recall("What is the secret code?", user_id="bob")
    bob_contents = set()
    for path in bob_result.all_paths:
        for m in path.memories:
            bob_contents.add(m.content)
    print(f"  Bob's recall for 'secret code': {bob_contents}")
    assert not any("alpha-bravo" in c for c in bob_contents)

    mem.close()


def test_separate_user_stats():
    """Each user should have independent stats (same instance)."""
    mem = _make_shared_memory()

    mem.add(user_id="user_a", messages=[
        {"role": "user", "content": "Message one"},
        {"role": "user", "content": "Message two"},
        {"role": "user", "content": "Message three"},
    ])
    mem.add(user_id="user_b", messages=[
        {"role": "user", "content": "Only one message here"},
    ])

    # Memories are in a flat dict so total is 4
    # But graph isolation means each user's graph is separate
    stats_a = mem.get_stats(user_id="user_a")
    stats_b = mem.get_stats(user_id="user_b")
    assert stats_a["nodes"] > 0
    assert stats_b["nodes"] > 0

    mem.close()


def test_agent_id_isolation():
    """Two agents under same user should have isolated memories when queried with agent_id."""
    mem = _make_shared_memory()

    mem.add(user_id="shared_user", agent_id="agent_a",
            messages=[{"role": "user", "content": "Agent A knows the password is foobar"}])
    mem.add(user_id="shared_user", agent_id="agent_b",
            messages=[{"role": "user", "content": "Agent B likes hiking in the mountains"}])

    mem.close()
