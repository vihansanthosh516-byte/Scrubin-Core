from scrubin.cognition.learning_state import LearningPattern, LearningState
from scrubin.cognition.belief_formation_engine import BeliefFormationEngine
from scrubin.world.state import WorldState


def _make_pattern(suffix: str, first_tick: int, description: str, confidence: float = 0.9) -> LearningPattern:
    return LearningPattern(
        pattern_id=f"pattern_{suffix}",
        pattern_type="REPETITIVE",
        description=description,
        occurrences=3,
        confidence=confidence,
        first_tick=first_tick,
        last_tick=first_tick + 10,
        source_observation_ids=(f"obs_{suffix}",),
    )


def _sanitize(text: str) -> str:
    sanitized = "".join(c if c.isalnum() else "_" for c in text)
    sanitized = "_".join(filter(None, sanitized.split("_")))
    return sanitized.lower()


def test_belief_generation_is_deterministic():
    # One pattern should produce a single deterministic belief.
    pattern = _make_pattern("energy", 10, "Energy dropped below 20%")
    learning_state = LearningState(observations=(), patterns=(pattern,), total_observations=0)
    world = WorldState(tick=100, learning_state=learning_state)
    engine = BeliefFormationEngine(rng=None)
    new_world = engine.evolve(world)
    beliefs = new_world.learning_state.beliefs
    assert len(beliefs) == 1
    b = beliefs[0]
    expected_id = f"belief_{_sanitize(pattern.description)}"
    assert b.belief_id == expected_id
    assert b.belief_type == "REPETITIVE_BELIEF"
    assert b.confidence == pattern.confidence
    assert b.supporting_pattern_ids == (pattern.pattern_id,)
    # created and updated tick should be current world tick
    assert b.created_tick == 100
    assert b.updated_tick == 100


def test_patterns_do_not_duplicate_beliefs():
    # Ensure that running the engine multiple times does not duplicate beliefs.
    # (Existing test already checks length and equality; retained.)
    pattern = _make_pattern("energy", 5, "Energy dropped below 20%")
    learning_state = LearningState(observations=(), patterns=(pattern,), total_observations=0)
    world = WorldState(tick=200, learning_state=learning_state)
    engine = BeliefFormationEngine(rng=None)
    first = engine.evolve(world)
    second = engine.evolve(first)
    assert len(first.learning_state.beliefs) == 1
    assert len(second.learning_state.beliefs) == 1
    assert first.learning_state.beliefs == second.learning_state.beliefs


def test_replay_produces_identical_beliefs():
    p1 = _make_pattern("a", 1, "Issue A")
    p2 = _make_pattern("b", 2, "Issue B")
    learning_state = LearningState(observations=(), patterns=(p1, p2), total_observations=0)
    world_a = WorldState(tick=50, learning_state=learning_state)
    world_b = WorldState(tick=50, learning_state=learning_state)
    engine = BeliefFormationEngine(rng=None)
    a = engine.evolve(world_a)
    b = engine.evolve(world_b)
    assert a.learning_state.beliefs == b.learning_state.beliefs


def test_belief_ordering_is_stable():
    # Ensure beliefs are sorted deterministically by belief_id.
    p1 = _make_pattern("z", 10, "Z issue")
    p2 = _make_pattern("a", 20, "A issue")
    learning_state = LearningState(observations=(), patterns=(p1, p2), total_observations=0)
    world = WorldState(tick=80, learning_state=learning_state)
    engine = BeliefFormationEngine(rng=None)
    new_world = engine.evolve(world)
    belief_ids = [b.belief_id for b in new_world.learning_state.beliefs]
    assert belief_ids == sorted(belief_ids)


def test_belief_confidence_updates_stably():
    # Confidence should exactly match pattern confidence and remain unchanged on repeat.
    pattern = _make_pattern("energy", 5, "Energy dropped below 20%", confidence=0.75)
    learning_state = LearningState(observations=(), patterns=(pattern,), total_observations=0)
    world = WorldState(tick=120, learning_state=learning_state)
    engine = BeliefFormationEngine(rng=None)
    world1 = engine.evolve(world)
    b1 = world1.learning_state.beliefs[0]
    assert b1.confidence == 0.75
    # Run again with same pattern; confidence should stay the same and not duplicate.
    world2 = engine.evolve(world1)
    b2 = world2.learning_state.beliefs[0]
    assert b2.confidence == 0.75
    assert b1 == b2

    # Patterns in unsorted order; beliefs should be sorted by belief_id.
    p1 = _make_pattern("z", 10, "Z issue")
    p2 = _make_pattern("a", 20, "A issue")
    learning_state = LearningState(observations=(), patterns=(p1, p2), total_observations=0)
    world = WorldState(tick=80, learning_state=learning_state)
    engine = BeliefFormationEngine(rng=None)
    new_world = engine.evolve(world)
    belief_ids = [b.belief_id for b in new_world.learning_state.beliefs]
    assert belief_ids == sorted(belief_ids)
