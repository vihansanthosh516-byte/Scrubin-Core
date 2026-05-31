from scrubin.cognition.learning_state import LearningObservation, LearningState
from scrubin.cognition.pattern_extraction_engine import PatternExtractionEngine
from scrubin.world.state import WorldState


def _make_observation(id_suffix: str, tick: int, lesson: str) -> LearningObservation:
    return LearningObservation(
        id=f"obs_{id_suffix}",
        tick=tick,
        source_reflection_id=f"ref_{id_suffix}",
        category="energy",
        lesson=lesson,
        confidence=1.0,
        severity=0.5,
        tags=("low_energy",),
    )


def test_pattern_generation_is_deterministic():
    # Three identical observations.
    obs1 = _make_observation("1", 10, "Energy dropped below 20%")
    obs2 = _make_observation("2", 20, "Energy dropped below 20%")
    obs3 = _make_observation("3", 30, "Energy dropped below 20%")
    learning_state = LearningState(observations=(obs1, obs2, obs3), learning_tick=30, total_observations=3)
    world = WorldState(tick=100, learning_state=learning_state)
    engine = PatternExtractionEngine(rng=None)
    new_world = engine.evolve(world)
    patterns = new_world.learning_state.patterns
    assert len(patterns) == 1
    p = patterns[0]
    assert p.pattern_id == "pattern_energy_dropped_below_20"
    assert p.occurrences == 3
    assert p.first_tick == 10
    assert p.last_tick == 30
    expected_confidence = 3 / (100 - 10 + 1)
    assert abs(p.confidence - expected_confidence) < 1e-12


def test_duplicate_observations_do_not_create_patterns():
    # Same observations applied twice should not create a second pattern.
    obs1 = _make_observation("1", 10, "Energy dropped below 20%")
    obs2 = _make_observation("2", 15, "Energy dropped below 20%")
    learning_state = LearningState(observations=(obs1, obs2), learning_tick=15, total_observations=2)
    world = WorldState(tick=200, learning_state=learning_state)
    engine = PatternExtractionEngine(rng=None)
    first = engine.evolve(world)
    second = engine.evolve(first)
    assert len(first.learning_state.patterns) == 1
    assert len(second.learning_state.patterns) == 1
    assert first.learning_state.patterns == second.learning_state.patterns


def test_replay_produces_identical_patterns():
    obs1 = _make_observation("1", 5, "Low blood pressure")
    obs2 = _make_observation("2", 7, "Low blood pressure")
    learning_state = LearningState(observations=(obs1, obs2), learning_tick=7, total_observations=2)
    world_a = WorldState(tick=50, learning_state=learning_state)
    world_b = WorldState(tick=50, learning_state=learning_state)
    engine = PatternExtractionEngine(rng=None)
    a = engine.evolve(world_a)
    b = engine.evolve(world_b)
    assert a.learning_state.patterns == b.learning_state.patterns


def test_pattern_ordering_is_stable():
    obs_alpha = _make_observation("a", 5, "Alpha issue")
    obs_beta = _make_observation("b", 6, "Beta issue")
    learning_state = LearningState(observations=(obs_alpha, obs_beta), learning_tick=6, total_observations=2)
    world = WorldState(tick=80, learning_state=learning_state)
    engine = PatternExtractionEngine(rng=None)
    new_world = engine.evolve(world)
    pattern_ids = [p.pattern_id for p in new_world.learning_state.patterns]
    assert pattern_ids == sorted(pattern_ids)
