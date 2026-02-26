"""Test 11: Multi-user and multi-agent isolation."""

from memwire import MemWire, MemWireConfig


def _make_config(user_id: str) -> MemWireConfig:
    return MemWireConfig(
        database_url="sqlite:///:memory:",
        user_id=user_id,
        qdrant_path=":memory:",
    )


def test_users_are_isolated():
    """User A's memories should not appear in User B's recall."""
    config_a = _make_config("alice")
    config_b = _make_config("bob")

    alice = MemWire(user_id="alice", config=config_a)
    bob = MemWire(user_id="bob", config=config_b)

    alice.add([{"role": "user", "content": "My secret code is alpha-bravo-42"}])
    bob.add([{"role": "user", "content": "I enjoy hiking in the mountains"}])

    alice_stats = alice.get_stats()
    bob_stats = bob.get_stats()

    assert alice_stats["memories"] == 1
    assert bob_stats["memories"] == 1

    # Bob should NOT see Alice's secret
    bob_result = bob.recall("What is the secret code?")
    bob_contents = set()
    for path in bob_result.all_paths:
        for mem in path.memories:
            bob_contents.add(mem.content)
    print(f"  Bob's recall for 'secret code': {bob_contents}")
    assert not any("alpha-bravo" in c for c in bob_contents)

    alice.close()
    bob.close()


def test_separate_user_stats():
    """Each user should have independent stats."""
    config_a = _make_config("user_a")
    config_b = _make_config("user_b")

    user_a = MemWire(user_id="user_a", config=config_a)
    user_b = MemWire(user_id="user_b", config=config_b)

    user_a.add([
        {"role": "user", "content": "Message one"},
        {"role": "user", "content": "Message two"},
        {"role": "user", "content": "Message three"},
    ])
    user_b.add([
        {"role": "user", "content": "Only one message here"},
    ])

    assert user_a.get_stats()["memories"] == 3
    assert user_b.get_stats()["memories"] == 1

    user_a.close()
    user_b.close()


def test_agent_id_isolation():
    """Two agents under same user should have isolated memories."""
    config = MemWireConfig(
        database_url="sqlite:///:memory:",
        user_id="shared_user",
        qdrant_path=":memory:",
    )

    agent_a = MemWire(user_id="shared_user", agent_id="agent_a", config=config)
    agent_a.add([{"role": "user", "content": "Agent A knows the password is foobar"}])

    agent_b = MemWire(user_id="shared_user", agent_id="agent_b", config=config)
    agent_b.add([{"role": "user", "content": "Agent B likes hiking in the mountains"}])

    assert agent_a.get_stats()["memories"] == 1
    assert agent_b.get_stats()["memories"] == 1

    agent_a.close()
    agent_b.close()
