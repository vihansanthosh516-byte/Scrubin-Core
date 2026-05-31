from scrubin.cognition.learning_state import LearningPattern, Belief, LearningState
from scrubin.cognition.belief_validation_engine import BeliefValidationEngine
from scrubin.world.state import WorldState

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_pattern(suffix: str, first_tick: int, confidence: float) -> LearningPattern:
    return LearningPattern(
        pattern_id=f"pat_{suffix}",
        pattern_type="REPETITIVE",
        description=f"Pattern {suffix}",
        occurrences=1,
        confidence=confidence,
        first_tick=first_tick,
        last_tick=first_tick + 1,
        source_observation_ids=(),
    )


def _make_belief(suffix: str, created_tick: int, supporting_pat_ids: tuple) -> Belief:
    return Belief(
        belief_id=f"belief_{suffix}",
        belief_type="REPETITIVE_BELIEF",
        description=f"Belief {suffix}",
        confidence=0.0,                 # will be recomputed by validation
        created_tick=created_tick,
        updated_tick=created_tick,
        supporting_pattern_ids=supporting_pat_ids,
        validation_state="STABLE",   # placeholder – overwritten
        support_count=len(supporting_pat_ids),
        contradiction_count=0,
        last_validated_tick=created_tick,
    )

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_validation_state_stable():
    # Confidence 0.9 → STABLE
    pat = _make_pattern("A", 5, 0.9)
    bel = _make_belief("A", 10, (pat.pattern_id,))
    learning_state = LearningState(
        observations=(),
        patterns=(pat,),
        beliefs=(bel,),
        total_observations=0,
    )
    world = WorldState(tick=100, learning_state=learning_state)
    engine = BeliefValidationEngine(rng=None)

    new_world = engine.evolve(world)
    new_bel = new_world.learning_state.beliefs[0]

    assert new_bel.confidence == 0.9
    assert new_bel.validation_state == "STABLE"
    assert new_bel.updated_tick == 100
    assert new_bel.last_validated_tick == 100
    assert new_bel.support_count == 1


def test_validation_state_weakened():
    # Confidence 0.6 → WEAKENING
    pat = _make_pattern("B", 5, 0.6)
    bel = _make_belief("B", 10, (pat.pattern_id,))
    learning_state = LearningState(
        observations=(),
        patterns=(pat,),
        beliefs=(bel,),
        total_observations=0,
    )
    world = WorldState(tick=200, learning_state=learning_state)
    engine = BeliefValidationEngine(rng=None)

    new_world = engine.evolve(world)
    new_bel = new_world.learning_state.beliefs[0]

    assert new_bel.confidence == 0.6
    assert new_bel.validation_state == "WEAKENING"
    assert new_bel.updated_tick == 200
    assert new_bel.last_validated_tick == 200


def test_validation_state_contradicted():
    # Confidence 0.2 → CONTRADICTED
    pat = _make_pattern("C", 5, 0.2)
    bel = _make_belief("C", 10, (pat.pattern_id,))
    learning_state = LearningState(
        observations=(),
        patterns=(pat,),
        beliefs=(bel,),
        total_observations=0,
    )
    world = WorldState(tick=300, learning_state=learning_state)
    engine = BeliefValidationEngine(rng=None)

    new_world = engine.evolve(world)
    new_bel = new_world.learning_state.beliefs[0]

    assert new_bel.confidence == 0.2
    assert new_bel.validation_state == "CONTRADICTED"
    assert new_bel.updated_tick == 300
    assert new_bel.last_validated_tick == 300


def test_validation_idempotence():
    # Running the engine twice should not change the belief.
    pat = _make_pattern("D", 5, 0.85)
    bel = _make_belief("D", 10, (pat.pattern_id,))
    learning_state = LearningState(
        observations=(),
        patterns=(pat,),
        beliefs=(bel,),
        total_observations=0,
    )
    world = WorldState(tick=400, learning_state=learning_state)
    engine = BeliefValidationEngine(rng=None)

    first = engine.evolve(world)
    second = engine.evolve(first)

    assert first.learning_state.beliefs == second.learning_state.beliefs
    b = first.learning_state.beliefs[0]
    assert b.updated_tick == 400
    assert b.last_validated_tick == 400