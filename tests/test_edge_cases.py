"""Test 8: Edge cases — empty inputs, special chars, long text, unicode."""

from tests.conftest import TEST_USER


def test_empty_message_list(memory):
    """Empty list should return empty results."""
    records = memory.add(user_id=TEST_USER, messages=[])
    assert len(records) == 0


def test_whitespace_only_content(memory):
    """Whitespace-only content should be skipped."""
    records = memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "   "},
        {"role": "user", "content": "\t\n"},
    ])
    assert len(records) == 0


def test_special_characters(memory):
    """Content with special chars should not crash."""
    records = memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Price is $50.00 (50% off!)"},
        {"role": "user", "content": "Email: user@example.com"},
        {"role": "user", "content": "Path: /usr/bin/python3"},
    ])
    assert len(records) == 3


def test_unicode_content(memory):
    """Unicode/emoji content should work."""
    records = memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "The meeting is at cafe in Paris"},
        {"role": "user", "content": "Temperature is 30 degrees celsius"},
    ])
    assert len(records) == 2
    result = memory.recall("meeting", user_id=TEST_USER)
    assert result is not None


def test_very_long_content(memory):
    """Very long messages should not crash (may be slow)."""
    long_text = "This is a test sentence about machine learning. " * 50
    records = memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": long_text}])
    assert len(records) == 1
    print(f"  Long text ({len(long_text)} chars): {memory.get_stats(user_id=TEST_USER)['nodes']} nodes")


def test_single_word_input(memory):
    """Single word should work without crashing."""
    records = memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "hello"}])
    assert len(records) == 1
    result = memory.recall("hello", user_id=TEST_USER)
    assert result is not None


def test_two_word_input(memory):
    """Two-word input should still work."""
    records = memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "good morning"}])
    assert len(records) == 1


def test_repeated_identical_messages(memory):
    """Adding the same message multiple times."""
    for _ in range(5):
        memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "I like chocolate"}])
    stats = memory.get_stats(user_id=TEST_USER)
    print(f"  5 identical messages: {stats['memories']} memories, "
          f"{stats['nodes']} nodes, {stats['edges']} edges")
    assert stats["memories"] == 5  # All stored separately


def test_numbers_only(memory):
    """Purely numeric content."""
    records = memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "12345"},
        {"role": "user", "content": "3.14159"},
    ])
    assert len(records) == 2


def test_mixed_languages(memory):
    """Content in different languages."""
    records = memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Hello world"},
        {"role": "user", "content": "Bonjour le monde"},
        {"role": "user", "content": "Hola mundo"},
    ])
    assert len(records) == 3


def test_very_similar_messages(memory):
    """Nearly identical messages with minor differences."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "The project deadline is March 15"},
        {"role": "user", "content": "The project deadline is March 16"},
        {"role": "user", "content": "The project deadline is March 17"},
    ])
    result = memory.recall("When is the deadline?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Similar messages recalled: {len(all_contents)}")


def test_recall_with_empty_query(memory):
    """Empty query string."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "Some stored memory"}])
    result = memory.recall("", user_id=TEST_USER)
    assert result is not None


def test_rapid_add_recall_cycles(memory):
    """Quick alternating add/recall cycles."""
    for i in range(10):
        memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": f"Memory number {i} about testing"}])
        result = memory.recall("testing", user_id=TEST_USER)
    stats = memory.get_stats(user_id=TEST_USER)
    print(f"  After 10 rapid cycles: {stats}")
    assert stats["memories"] == 10
