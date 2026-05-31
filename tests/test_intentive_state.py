'''Tests for the AutonomousIntent and IntentiveCognitionState data structures.

These tests verify that required fields exist, that the ``with_*`` helpers
behave deterministically (sorting tuples, clamping numeric ranges), and that
the container correctly adds intents, maintains sorted collections, and
selects a dominant intent according to the specification.
'''

from scrubin.cognition.intentive_state import AutonomousIntent, IntentiveCognitionState


def test_autonomous_intent_fields_and_helpers():
    # Basic construction with mandatory fields only
    intent = AutonomousIntent(id="i1", description="test", urgency=0.5, confidence=0.8)
    assert intent.id == "i1"
    # Alias property
    assert intent.intent_id == "i1"

    # ``with_semantic_tags`` sorts tags deterministically
    intent2 = intent.with_semantic_tags(("b", "a", "c"))
    assert intent2.semantic_tags == ("a", "b", "c")

    # ``with_urgency`` clamps to [0.0, 1.0]
    assert intent.with_urgency(-0.1).urgency == 0.0
    assert intent.with_urgency(1.5).urgency == 1.0

    # ``with_confidence`` clamps similarly
    assert intent.with_confidence(-0.2).confidence == 0.0
    assert intent.with_confidence(2.0).confidence == 1.0


def test_intentive_cognition_state_operations_and_dominant_intent():
    state = IntentiveCognitionState()
    # Two intents with different urgency & confidence values
    intent_a = AutonomousIntent(id="a", description="a", urgency=0.2, confidence=0.9)
    intent_b = AutonomousIntent(id="b", description="b", urgency=0.5, confidence=0.5)
    # Add in reverse order to test sorting by id
    state = state.add_intent(intent_b).add_intent(intent_a)
    # Active intents should be sorted by id (a, b)
    assert state.active_intents == (intent_a, intent_b)

    # Compute dominant intent – should pick the one with higher urgency (b)
    state = state.compute_dominant_intent()
    assert state.dominant_intent.id == "b"

    # Suppress the dominant intent and recompute – now a becomes dominant
    state = state.suppress_intent("b")
    # ``suppress_intent`` does not recompute dominant, so do it manually
    state = state.compute_dominant_intent()
    assert state.dominant_intent.id == "a"
    # Ensure the suppressed collection contains the right intent
    assert any(i.id == "b" for i in state.suppressed_intents)
