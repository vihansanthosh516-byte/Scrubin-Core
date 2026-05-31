from scrubin.cognition.learning_state import LearningObservation, LearningPattern, Belief, LearningState
from scrubin.cognition.knowledge_graph_engine import KnowledgeGraphEngine
from scrubin.world.state import WorldState


def _make_observation(suffix: str, tick: int, lesson: str) -> LearningObservation:
    return LearningObservation(
        id=f"obs_{suffix}",
        tick=tick,
        source_reflection_id=f"ref_{suffix}",
        category="energy",
        lesson=lesson,
        confidence=1.0,
        severity=0.5,
        tags=("low_energy",),
    )


def _make_pattern(suffix: str, first_tick: int, description: str, source_obs_ids: tuple) -> LearningPattern:
    return LearningPattern(
        pattern_id=f"pat_{suffix}",
        pattern_type="REPETITIVE",
        description=description,
        occurrences=len(source_obs_ids),
        confidence=0.9,
        first_tick=first_tick,
        last_tick=first_tick + 5,
        source_observation_ids=source_obs_ids,
    )


def _make_belief(suffix: str, created_tick: int, description: str, supporting_pat_ids: tuple) -> Belief:
    return Belief(
        belief_id=f"belief_{suffix}",
        belief_type="REPETITIVE_BELIEF",
        description=description,
        confidence=0.9,
        created_tick=created_tick,
        updated_tick=created_tick,
        supporting_pattern_ids=supporting_pat_ids,
        validation_state="STABLE",
        support_count=len(supporting_pat_ids),
        contradiction_count=0,
        last_validated_tick=created_tick,
    )


def test_knowledge_graph_construction_is_deterministic():
    # Build simple chain: Observation -> Pattern -> Belief
    obs = _make_observation("e1", 5, "Energy dropped below 20%")
    pat = _make_pattern("e1", 5, "Low energy pattern", (obs.id,))
    bel = _make_belief("e1", 10, "Energy is limiting factor", (pat.pattern_id,))
    learning_state = LearningState(
        observations=(obs,),
        patterns=(pat,),
        beliefs=(bel,),
        total_observations=1,
    )
    world = WorldState(tick=100, learning_state=learning_state)
    engine = KnowledgeGraphEngine(rng=None)
    new_world = engine.evolve(world)
    graph = new_world.knowledge_graph
    # Three nodes expected.
    assert len(graph.nodes) == 3
    node_ids = {n.node_id for n in graph.nodes}
    assert obs.id in node_ids
    assert pat.pattern_id in node_ids
    assert bel.belief_id in node_ids
    # Two edges expected: obs->pat and pat->bel.
    assert len(graph.edges) == 2
    edge_tuples = {(e.source_id, e.target_id, e.edge_type) for e in graph.edges}
    assert (obs.id, pat.pattern_id, "SUPPORTS") in edge_tuples
    assert (pat.pattern_id, bel.belief_id, "SUPPORTS") in edge_tuples


def test_knowledge_graph_idempotence():
    obs = _make_observation("e2", 5, "Energy low")
    pat = _make_pattern("e2", 5, "Pattern low", (obs.id,))
    bel = _make_belief("e2", 10, "Belief low", (pat.pattern_id,))
    learning_state = LearningState(observations=(obs,), patterns=(pat,), beliefs=(bel,), total_observations=1)
    world = WorldState(tick=50, learning_state=learning_state)
    engine = KnowledgeGraphEngine(rng=None)
    first = engine.evolve(world)
    second = engine.evolve(first)
    assert first.knowledge_graph.nodes == second.knowledge_graph.nodes
    assert first.knowledge_graph.edges == second.knowledge_graph.edges


def test_knowledge_graph_replay_consistency():
    obs = _make_observation("e3", 5, "Energy low again")
    pat = _make_pattern("e3", 5, "Pattern again", (obs.id,))
    bel = _make_belief("e3", 10, "Belief again", (pat.pattern_id,))
    learning_state = LearningState(observations=(obs,), patterns=(pat,), beliefs=(bel,), total_observations=1)
    world_a = WorldState(tick=80, learning_state=learning_state)
    world_b = WorldState(tick=80, learning_state=learning_state)
    engine = KnowledgeGraphEngine(rng=None)
    a = engine.evolve(world_a)
    b = engine.evolve(world_b)
    assert a.knowledge_graph.nodes == b.knowledge_graph.nodes
    assert a.knowledge_graph.edges == b.knowledge_graph.edges


def test_knowledge_graph_ordering_is_stable():
    # Nodes/edges should be sorted deterministically.
    obs1 = _make_observation("z", 5, "Z issue")
    obs2 = _make_observation("a", 6, "A issue")
    pat1 = _make_pattern("z", 5, "Z pattern", (obs1.id,))
    pat2 = _make_pattern("a", 6, "A pattern", (obs2.id,))
    bel1 = _make_belief("z", 10, "Z belief", (pat1.pattern_id,))
    bel2 = _make_belief("a", 12, "A belief", (pat2.pattern_id,))
    learning_state = LearningState(
        observations=(obs1, obs2),
        patterns=(pat1, pat2),
        beliefs=(bel1, bel2),
        total_observations=2,
    )
    world = WorldState(tick=120, learning_state=learning_state)
    engine = KnowledgeGraphEngine(rng=None)
    new_world = engine.evolve(world)
    node_ids = [n.node_id for n in new_world.knowledge_graph.nodes]
    edge_ids = [(e.source_id, e.target_id, e.edge_type) for e in new_world.knowledge_graph.edges]
    assert node_ids == sorted(node_ids)
    assert edge_ids == sorted(edge_ids)
