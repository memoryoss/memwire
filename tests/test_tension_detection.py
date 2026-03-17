"""Test 4: Tension/contradiction detection."""

from tests.conftest import TEST_USER


def test_direct_contradiction(memory):
    """Explicit opposites should be detected as tension."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "I love spicy food, the spicier the better"},
        {"role": "user", "content": "I hate spicy food, it upsets my stomach"},
    ])
    result = memory.recall("Does the user like spicy food?", user_id=TEST_USER)
    print(f"  Direct contradiction: {len(result.supporting)} supporting, "
          f"{len(result.conflicting)} conflicting")
    print(f"  has_conflicts: {result.has_conflicts}")


def test_preference_change_over_time(memory):
    """Later preference contradicts earlier one."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "I prefer using Python for all projects"},
    ])
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "I have switched to Rust and no longer use Python"},
    ])
    result = memory.recall("What programming language does the user prefer?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Preference change: {all_contents}")
    print(f"  Conflicts: {result.has_conflicts}")


def test_subtle_contradiction(memory):
    """Contradictions that aren't word-for-word opposites."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Our company policy requires all employees to work from office"},
        {"role": "user", "content": "We allow fully remote work for all team members"},
    ])
    result = memory.recall("What is the remote work policy?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Subtle contradiction: {all_contents}")
    print(f"  Conflicts: {result.has_conflicts}")


def test_no_tension_for_complementary_info(memory):
    """Related but non-contradictory info should NOT trigger tension."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Our main office is in New York"},
        {"role": "user", "content": "We have a branch office in London"},
        {"role": "user", "content": "The Tokyo office opened last year"},
    ])
    result = memory.recall("Where are our offices?", user_id=TEST_USER)
    print(f"  Complementary info: {len(result.supporting)} supporting, "
          f"{len(result.conflicting)} conflicting")


def test_numeric_contradiction(memory):
    """Conflicting numbers about the same thing."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "The project budget is 100 thousand dollars"},
        {"role": "user", "content": "The project budget is 50 thousand dollars"},
    ])
    result = memory.recall("What is the project budget?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Numeric contradiction: {all_contents}")
    print(f"  Conflicts: {result.has_conflicts}")


def test_partially_overlapping_info(memory):
    """Some overlap, some contradiction."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Vendor A provides organic cotton at 10 dollars per yard"},
        {"role": "user", "content": "Vendor A provides organic cotton at 15 dollars per yard"},
        {"role": "user", "content": "Vendor A is reliable and delivers on time"},
    ])
    result = memory.recall("What do we know about Vendor A pricing?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Partial overlap: {all_contents}")
    print(f"  Conflicts: {result.has_conflicts}")
