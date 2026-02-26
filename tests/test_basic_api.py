"""Test 1: Basic API — add, recall, feedback, search, anchors, stats."""


def test_add_single_message(memory):
    records = memory.add([{"role": "user", "content": "I like pizza"}])
    assert len(records) == 1
    assert records[0].content == "I like pizza"
    assert records[0].role == "user"


def test_add_multiple_messages(memory):
    records = memory.add([
        {"role": "user", "content": "Hello there"},
        {"role": "assistant", "content": "Hi, how can I help?"},
        {"role": "user", "content": "Tell me about weather"},
    ])
    assert len(records) == 3


def test_add_skips_empty_content(memory):
    records = memory.add([
        {"role": "user", "content": "Valid message"},
        {"role": "user", "content": ""},
        {"role": "user", "content": "   "},
    ])
    assert len(records) == 1


def test_add_missing_role_defaults_to_user(memory):
    records = memory.add([{"content": "No role here"}])
    assert records[0].role == "user"


def test_add_missing_content_skipped(memory):
    records = memory.add([{"role": "user"}])
    assert len(records) == 0


def test_recall_returns_result(seeded_memory):
    result = seeded_memory.recall("What materials do we prefer?")
    assert result.query == "What materials do we prefer?"
    assert isinstance(result.supporting, list)
    assert isinstance(result.conflicting, list)


def test_recall_has_formatted_output(seeded_memory):
    result = seeded_memory.recall("organic materials")
    assert isinstance(result.formatted, str)


def test_recall_on_empty_memory(memory):
    result = memory.recall("anything")
    assert len(result.supporting) == 0
    assert len(result.conflicting) == 0
    assert result.formatted == ""


def test_feedback_without_prior_recall(memory):
    stats = memory.feedback(response="some response")
    assert stats == {"strengthened": 0, "weakened": 0}


def test_feedback_after_recall(seeded_memory):
    seeded_memory.recall("organic materials")
    stats = seeded_memory.feedback(response="We should use organic cotton from Vendor A")
    assert "strengthened" in stats
    assert "weakened" in stats


def test_search_returns_results(seeded_memory):
    results = seeded_memory.search("organic")
    assert len(results) > 0
    # Results are (MemoryRecord, score) tuples
    record, score = results[0]
    assert hasattr(record, "content")
    assert 0.0 <= score <= 1.0


def test_search_with_category_filter(seeded_memory):
    results_all = seeded_memory.search("materials")
    results_filtered = seeded_memory.search("materials", category="nonexistent_category")
    assert len(results_filtered) == 0
    assert len(results_all) > 0


def test_search_top_k(seeded_memory):
    results = seeded_memory.search("budget", top_k=2)
    assert len(results) <= 2


def test_add_anchor(memory):
    memory.add_anchor("pricing", "This is about product pricing and costs")
    anchors = memory.engine.classifier.get_anchors()
    assert "pricing" in anchors


def test_get_stats(seeded_memory):
    stats = seeded_memory.get_stats()
    assert stats["memories"] == 6
    assert stats["nodes"] > 0
    assert stats["edges"] > 0
    assert "fact" in stats["anchors"]
    assert "knowledge_bases" in stats


def test_close_is_safe(memory):
    memory.add([{"role": "user", "content": "test"}])
    memory.close()  # Should not raise
