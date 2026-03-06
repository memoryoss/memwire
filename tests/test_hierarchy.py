"""Test: Hierarchical isolation — app_id, workspace_id, multi-tenant via single instance."""

from memwire import MemWire, MemWireConfig


def _make_shared_memory() -> MemWire:
    config = MemWireConfig(
        database_url="sqlite:///:memory:",
        org_id="test_org",
        qdrant_path=":memory:",
    )
    return MemWire(config=config)


def test_app_id_isolation():
    """Same user, different app_id should have isolated graphs."""
    mem = _make_shared_memory()

    mem.add(user_id="alice", app_id="app1",
            messages=[{"role": "user", "content": "App1 secret: the launch code is delta-9"}])
    mem.add(user_id="alice", app_id="app2",
            messages=[{"role": "user", "content": "App2 info: I like hiking in the mountains"}])

    # Recall within app1 should not return app2 content
    result_app1 = mem.recall("What is the secret?", user_id="alice", app_id="app1")
    app1_contents = set()
    for path in result_app1.all_paths:
        for m in path.memories:
            app1_contents.add(m.content)
    print(f"  App1 recall: {app1_contents}")

    # Recall within app2 should not return app1 content
    result_app2 = mem.recall("What is the secret?", user_id="alice", app_id="app2")
    app2_contents = set()
    for path in result_app2.all_paths:
        for m in path.memories:
            app2_contents.add(m.content)
    print(f"  App2 recall: {app2_contents}")

    # App2 should NOT see app1's secret
    assert not any("delta-9" in c for c in app2_contents), \
        f"App2 should not see app1's data: {app2_contents}"

    mem.close()


def test_workspace_isolation():
    """Same user, different workspace should have isolated graphs."""
    mem = _make_shared_memory()

    mem.add(user_id="alice", workspace_id="ws1",
            messages=[{"role": "user", "content": "Workspace 1 project: building a rocket"}])
    mem.add(user_id="alice", workspace_id="ws2",
            messages=[{"role": "user", "content": "Workspace 2 project: writing a novel"}])

    result_ws1 = mem.recall("What project are we working on?", user_id="alice", workspace_id="ws1")
    ws1_contents = set()
    for path in result_ws1.all_paths:
        for m in path.memories:
            ws1_contents.add(m.content)

    result_ws2 = mem.recall("What project are we working on?", user_id="alice", workspace_id="ws2")
    ws2_contents = set()
    for path in result_ws2.all_paths:
        for m in path.memories:
            ws2_contents.add(m.content)

    print(f"  WS1 recall: {ws1_contents}")
    print(f"  WS2 recall: {ws2_contents}")

    # WS2 should NOT see WS1's rocket project
    assert not any("rocket" in c for c in ws2_contents), \
        f"WS2 should not see WS1 data: {ws2_contents}"

    mem.close()


def test_cross_user_graph_isolation():
    """Bob's recall should never traverse Alice's graph nodes."""
    mem = _make_shared_memory()

    mem.add(user_id="alice",
            messages=[{"role": "user", "content": "Alice's password is super-secret-123"}])
    mem.add(user_id="bob",
            messages=[{"role": "user", "content": "Bob enjoys playing guitar"}])

    # Bob recalls — should not get Alice's password
    bob_result = mem.recall("What is the password?", user_id="bob")
    bob_contents = set()
    for path in bob_result.all_paths:
        for m in path.memories:
            bob_contents.add(m.content)
    print(f"  Bob's recall for 'password': {bob_contents}")
    assert not any("super-secret" in c for c in bob_contents), \
        f"Bob should not see Alice's data: {bob_contents}"

    mem.close()


def test_hierarchy_stats_isolation():
    """Stats should reflect the correct user/app scope."""
    mem = _make_shared_memory()

    mem.add(user_id="alice", app_id="app1", messages=[
        {"role": "user", "content": "Message 1 for app1"},
        {"role": "user", "content": "Message 2 for app1"},
    ])
    mem.add(user_id="alice", app_id="app2", messages=[
        {"role": "user", "content": "Message 1 for app2"},
    ])

    stats_app1 = mem.get_stats(user_id="alice", app_id="app1")
    stats_app2 = mem.get_stats(user_id="alice", app_id="app2")

    print(f"  App1 stats: {stats_app1}")
    print(f"  App2 stats: {stats_app2}")

    # Each app's graph should have its own nodes
    assert stats_app1["nodes"] > 0
    assert stats_app2["nodes"] > 0

    mem.close()


def test_same_instance_multi_user_add_recall():
    """Multiple users on the same MemWire instance with interleaved operations."""
    mem = _make_shared_memory()

    # Interleave adds from multiple users
    mem.add(user_id="alice", messages=[{"role": "user", "content": "Alice likes cats"}])
    mem.add(user_id="bob", messages=[{"role": "user", "content": "Bob likes dogs"}])
    mem.add(user_id="alice", messages=[{"role": "user", "content": "Alice also likes birds"}])
    mem.add(user_id="bob", messages=[{"role": "user", "content": "Bob also likes fish"}])

    # Each user should recall their own memories
    alice_result = mem.recall("What animals do I like?", user_id="alice")
    alice_contents = set()
    for path in alice_result.all_paths:
        for m in path.memories:
            alice_contents.add(m.content)

    bob_result = mem.recall("What animals do I like?", user_id="bob")
    bob_contents = set()
    for path in bob_result.all_paths:
        for m in path.memories:
            bob_contents.add(m.content)

    print(f"  Alice's animals: {alice_contents}")
    print(f"  Bob's animals: {bob_contents}")

    # Bob should not see Alice's cats/birds
    assert not any("cats" in c or "birds" in c for c in bob_contents), \
        f"Bob should not see Alice's data: {bob_contents}"

    mem.close()
