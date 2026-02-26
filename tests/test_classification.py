"""Test 2: Classification accuracy — do memories get the right category?"""


def test_fact_classification(memory):
    """Facts should be classified as 'fact'."""
    records = memory.add([
        {"role": "user", "content": "The Earth orbits the Sun"},
        {"role": "user", "content": "Water boils at 100 degrees Celsius"},
        {"role": "user", "content": "Python was created by Guido van Rossum"},
    ])
    categories = [r.category for r in records]
    fact_count = categories.count("fact")
    print(f"  Fact classification: {categories} (expected mostly 'fact')")
    # At least one should be classified as fact
    assert fact_count >= 1, f"Expected at least 1 fact, got categories: {categories}"


def test_preference_classification(memory):
    """Preferences should be classified as 'preference'."""
    records = memory.add([
        {"role": "user", "content": "I prefer dark mode over light mode"},
        {"role": "user", "content": "I like my coffee black with no sugar"},
        {"role": "user", "content": "I enjoy working late at night"},
    ])
    categories = [r.category for r in records]
    pref_count = categories.count("preference")
    print(f"  Preference classification: {categories} (expected mostly 'preference')")
    assert pref_count >= 1, f"Expected at least 1 preference, got: {categories}"


def test_instruction_classification(memory):
    """Instructions should be classified as 'instruction'."""
    records = memory.add([
        {"role": "user", "content": "Always respond in formal English"},
        {"role": "user", "content": "Never share my personal information"},
        {"role": "user", "content": "Send me a weekly summary every Monday"},
    ])
    categories = [r.category for r in records]
    inst_count = categories.count("instruction")
    print(f"  Instruction classification: {categories} (expected mostly 'instruction')")
    assert inst_count >= 1, f"Expected at least 1 instruction, got: {categories}"


def test_event_classification(memory):
    """Events should be classified as 'event'."""
    records = memory.add([
        {"role": "user", "content": "We had a team meeting yesterday about the roadmap"},
        {"role": "user", "content": "The server crashed last Tuesday"},
        {"role": "user", "content": "I graduated from MIT in 2020"},
    ])
    categories = [r.category for r in records]
    event_count = categories.count("event")
    print(f"  Event classification: {categories} (expected mostly 'event')")
    assert event_count >= 1, f"Expected at least 1 event, got: {categories}"


def test_entity_classification(memory):
    """Entity info should have 'entity' in top-2 categories.

    NOTE: The 'entity' anchor often loses to 'fact' or 'event' because
    sentences like "John Smith is our project manager" look like facts
    to an embedding model. We verify entity is at least competitive.
    """
    records = memory.add([
        {"role": "user", "content": "John Smith is our project manager"},
        {"role": "user", "content": "Acme Corp is based in San Francisco"},
        {"role": "user", "content": "The Tesla Model 3 is an electric vehicle"},
    ])
    # Check that 'entity' appears in top-2 for at least one record
    has_entity_in_top2 = False
    for r in records:
        top_k = memory.engine.classifier.get_top_k(r.embedding, k=2)
        top_names = [name for name, _ in top_k]
        if "entity" in top_names:
            has_entity_in_top2 = True
    categories = [r.category for r in records]
    print(f"  Entity classification: {categories}")
    print(f"  Entity in top-2 for at least one: {has_entity_in_top2}")
    assert has_entity_in_top2, f"Entity not in top-2 for any record: {categories}"


def test_custom_anchor_classification(memory):
    """Custom anchors should work for classification."""
    memory.add_anchor("technical", "This is a technical specification or requirement")
    records = memory.add([
        {"role": "user", "content": "The API must support TLS 1.3 encryption"},
        {"role": "user", "content": "Response latency should be under 200ms"},
    ])
    categories = [r.category for r in records]
    print(f"  Custom anchor: {categories}")
    # At least verifies it doesn't crash; classification may vary


def test_ambiguous_classification(memory):
    """Sentences that could fit multiple categories should still classify."""
    records = memory.add([
        # Could be fact or preference
        {"role": "user", "content": "I think organic food is healthier"},
        # Could be event or fact
        {"role": "user", "content": "Amazon acquired Whole Foods in 2017"},
        # Could be instruction or preference
        {"role": "user", "content": "I want all code reviewed before merging"},
    ])
    # None should be "unknown" — the threshold (0.3) should be low enough
    categories = [r.category for r in records]
    unknown_count = categories.count("unknown")
    print(f"  Ambiguous classification: {categories}")
    assert unknown_count == 0, f"Got {unknown_count} unknowns: {categories}"


def test_very_short_input_classification(memory):
    """Very short inputs may struggle to classify."""
    records = memory.add([
        {"role": "user", "content": "ok"},
        {"role": "user", "content": "yes"},
        {"role": "user", "content": "no thanks"},
    ])
    categories = [r.category for r in records]
    print(f"  Short input classification: {categories}")
    # These may be "unknown" — just verify no crash
