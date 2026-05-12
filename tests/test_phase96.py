from scrubin.world.model import SimulationWorld
from scrubin.learning.distillation import MCTSDistiller, MCTSTrace
from scrubin.learning.hybrid_priors import (
    LearnedPriorProvider, PriorGuidedSelector, BranchPrior, PriorConfig,
    PriorIntegrationResult, _softmax,
)
from scrubin.learning.hybrid_rollout import (
    LearnedRolloutPolicy, MortalityAwareRolloutGuidance, AdaptiveRolloutSelector,
    HybridRolloutConfig, RolloutGuidanceResult,
)
from scrubin.learning.hybrid_value import (
    LearnedValueEstimator, HybridValueBlender, DynamicWeightAdjuster,
    HybridValueConfig, ValueEstimate,
)
from scrubin.learning.hybrid_pruning import (
    LearnedPruningHints, HybridMCTSIntegrator, PruningConfig, PruningDecision,
)
from scrubin.decision.mcts import SearchNode
from scrubin.decision.planning import PlanningState
from scrubin.decision.utility import UtilityFunction, UtilityWeights


def _make_world():
    return SimulationWorld()


def _make_node(world=None, depth=0):
    w = world or _make_world()
    state = PlanningState(world=w, depth=depth)
    return SearchNode(state=state)


def test_softmax_basic():
    result = _softmax({"a": 1.0, "b": 2.0, "c": 3.0}, temperature=1.0)
    assert abs(sum(result.values()) - 1.0) < 1e-6
    assert result["c"] > result["b"] > result["a"]


def test_softmax_empty():
    result = _softmax({})
    assert result == {}


def test_softmax_temperature():
    hot = _softmax({"a": 1.0, "b": 5.0}, temperature=10.0)
    cold = _softmax({"a": 1.0, "b": 5.0}, temperature=0.1)
    assert hot["a"] > cold["a"]


def test_branch_prior_to_dict():
    bp = BranchPrior(action="intubation", prior_probability=0.6, source="learned")
    d = bp.to_dict()
    assert d["action"] == "intubation"
    assert d["prior_probability"] == 0.6


def test_prior_config_defaults():
    c = PriorConfig()
    assert c.prior_weight == 0.25
    assert c.fallback_to_uniform is True


def test_prior_integration_result_to_dict():
    r = PriorIntegrationResult(
        world_hash="abc",
        priors=[BranchPrior(action="a", prior_probability=0.5)],
        applied=True,
        source="learned",
    )
    d = r.to_dict()
    assert d["world_hash"] == "abc"
    assert d["applied"] is True


def test_learned_prior_provider_no_fn():
    provider = LearnedPriorProvider()
    w = _make_world()
    priors = provider.get_priors(w)
    assert isinstance(priors, dict)
    assert not provider.has_priors(w)


def test_learned_prior_provider_custom_fn():
    def custom_fn(world):
        return {"intubation": 0.5, "monitor": 0.2, "wait": 0.3}
    provider = LearnedPriorProvider(custom_prior_fn=custom_fn)
    w = _make_world()
    priors = provider.get_priors(w)
    assert "intubation" in priors
    assert abs(sum(priors.values()) - 1.0) < 1e-6


def test_learned_prior_provider_cache():
    call_count = [0]
    def custom_fn(world):
        call_count[0] += 1
        return {"monitor": 1.0}
    provider = LearnedPriorProvider(custom_prior_fn=custom_fn)
    w = _make_world()
    provider.get_priors(w)
    provider.get_priors(w)
    assert call_count[0] == 1


def test_learned_prior_provider_clear_cache():
    call_count = [0]
    def custom_fn(world):
        call_count[0] += 1
        return {"monitor": 1.0}
    provider = LearnedPriorProvider(custom_prior_fn=custom_fn)
    w = _make_world()
    provider.get_priors(w)
    provider.clear_cache()
    provider.get_priors(w)
    assert call_count[0] == 2


def test_learned_prior_provider_distiller():
    distiller = MCTSDistiller()
    from scrubin.replay.hash import world_hash
    w = _make_world()
    w_hash = world_hash(w)
    trace = MCTSTrace(
        tick=0,
        world_hash=w_hash,
        action_priors={0: 0.3, 3: 0.7},
        selected_action=3,
        value_estimate=0.8,
    )
    distiller.add_trace(trace)
    provider = LearnedPriorProvider(distiller=distiller)
    priors = provider.get_priors(w)
    assert len(priors) > 0


def test_prior_guided_selector_no_priors():
    provider = LearnedPriorProvider()
    selector = PriorGuidedSelector(prior_provider=provider)
    root = _make_node()
    child = SearchNode(state=PlanningState(world=_make_world()), parent=root, action="monitor")
    child.visits = 5
    child.value = 10.0
    root.children.append(child)
    result = selector.select_with_priors(root)
    assert result is child


def test_prior_guided_selector_with_priors():
    def fn(world):
        return {"monitor": 0.8, "wait": 0.2}
    provider = LearnedPriorProvider(custom_prior_fn=fn)
    selector = PriorGuidedSelector(prior_provider=provider)
    root = _make_node()
    child1 = SearchNode(state=PlanningState(world=_make_world()), parent=root, action="monitor")
    child1.visits = 3
    child1.value = 6.0
    child2 = SearchNode(state=PlanningState(world=_make_world()), parent=root, action="wait")
    child2.visits = 3
    child2.value = 6.0
    root.children = [child1, child2]
    result = selector.select_with_priors(root)
    assert result.action in ("monitor", "wait")


def test_prior_guided_selector_apply_expansion():
    def fn(world):
        return {"monitor": 0.6, "intubation": 0.4}
    provider = LearnedPriorProvider(custom_prior_fn=fn)
    selector = PriorGuidedSelector(prior_provider=provider)
    root = _make_node()
    child1 = SearchNode(state=PlanningState(world=_make_world()), parent=root, action="monitor")
    child2 = SearchNode(state=PlanningState(world=_make_world()), parent=root, action="intubation")
    result = selector.apply_expansion_priors(root, [child1, child2])
    assert result.applied
    assert len(result.priors) == 2


def test_prior_guided_selector_log():
    provider = LearnedPriorProvider()
    selector = PriorGuidedSelector(prior_provider=provider)
    root = _make_node()
    child = SearchNode(state=PlanningState(world=_make_world()), parent=root, action="monitor")
    selector.apply_expansion_priors(root, [child])
    assert len(selector.integration_log) == 1
    selector.clear_log()
    assert len(selector.integration_log) == 0


def test_hybrid_rollout_config_defaults():
    c = HybridRolloutConfig()
    assert c.learned_weight == 0.6
    assert c.heuristic_weight == 0.3
    assert c.random_weight == 0.1


def test_rollout_guidance_result_to_dict():
    r = RolloutGuidanceResult(action="intubation", source="learned", confidence=0.8)
    d = r.to_dict()
    assert d["action"] == "intubation"
    assert d["source"] == "learned"


def test_learned_rollout_policy_no_fn():
    policy = LearnedRolloutPolicy(config=HybridRolloutConfig(learned_weight=0.0, heuristic_weight=1.0, random_weight=0.0))
    w = _make_world()
    actions = ["monitor", "wait", "intubation"]
    result = policy.select_action(w, actions)
    assert result.action in actions
    assert result.source == "heuristic"


def test_learned_rollout_policy_with_guidance():
    def guide(world, actions):
        return "intubation" if "intubation" in actions else None
    policy = LearnedRolloutPolicy(guidance_fn=guide, config=HybridRolloutConfig(learned_weight=1.0, heuristic_weight=0.0, random_weight=0.0))
    w = _make_world()
    result = policy.select_action(w, ["intubation", "monitor"])
    assert result.action == "intubation"
    assert result.source == "learned"


def test_learned_rollout_policy_source_distribution():
    policy = LearnedRolloutPolicy(config=HybridRolloutConfig(learned_weight=0.0, heuristic_weight=0.0, random_weight=1.0))
    w = _make_world()
    for _ in range(5):
        policy.select_action(w, ["monitor", "wait"])
    dist = policy.source_distribution
    assert "random" in dist
    assert dist["random"] == 5


def test_mortality_aware_guidance_critical():
    guidance = MortalityAwareRolloutGuidance()
    w = _make_world()
    w.mortality_risk = 0.8
    w.physiology.vitals["spo2"] = 60
    result = guidance.guide(w, ["intubation", "emergency_airway", "monitor"])
    assert result == "emergency_airway"


def test_mortality_aware_guidance_stable():
    guidance = MortalityAwareRolloutGuidance()
    w = _make_world()
    w.mortality_risk = 0.05
    result = guidance.guide(w, ["monitor", "wait"])
    assert result is None


def test_adaptive_rollout_selector():
    selector = AdaptiveRolloutSelector(config=HybridRolloutConfig(learned_weight=0.5, heuristic_weight=0.3, random_weight=0.2))
    w = _make_world()
    action = selector.select_action(w, ["monitor", "wait", "intubation"], recent_performance=-3.0)
    assert action in ["monitor", "wait", "intubation"]
    weights = selector.current_weights
    assert "learned" in weights
    assert "heuristic" in weights
    assert "random" in weights


def test_hybrid_value_config_defaults():
    c = HybridValueConfig()
    assert c.learned_weight == 0.4
    assert c.mcts_weight == 0.6


def test_value_estimate_to_dict():
    ve = ValueEstimate(mcts_value=0.5, learned_value=0.7, blended_value=0.58, effective_weight_learned=0.4, source="blended")
    d = ve.to_dict()
    assert d["mcts_value"] == 0.5
    assert d["blended_value"] == 0.58


def test_learned_value_estimator_no_fn():
    estimator = LearnedValueEstimator()
    w = _make_world()
    val = estimator.estimate(w)
    assert val == 0.0
    assert not estimator.has_estimate(w)


def test_learned_value_estimator_custom_fn():
    def val_fn(world):
        return 1.0 - world.mortality_risk
    estimator = LearnedValueEstimator(value_fn=val_fn)
    w = _make_world()
    val = estimator.estimate(w)
    assert 0.0 <= val <= 1.0
    assert estimator.has_estimate(w)


def test_hybrid_value_blender_fallback():
    estimator = LearnedValueEstimator()
    utility = UtilityFunction()
    blender = HybridValueBlender(learned_estimator=estimator, utility_function=utility)
    node = _make_node()
    result = blender.blend(node, mcts_value=0.5)
    assert result.source == "mcts_fallback"
    assert result.blended_value == 0.5


def test_hybrid_value_blender_blended():
    def val_fn(world):
        return 0.8
    estimator = LearnedValueEstimator(value_fn=val_fn)
    blender = HybridValueBlender(learned_estimator=estimator, config=HybridValueConfig(learned_weight=0.4, mcts_weight=0.6, blend_dynamically=False))
    node = _make_node()
    result = blender.blend(node, mcts_value=0.5)
    assert result.source == "blended"
    expected = 0.4 * 0.8 + 0.6 * 0.5
    assert abs(result.blended_value - expected) < 1e-6


def test_hybrid_value_blender_dynamic_adjusts():
    def val_fn(world):
        return 0.8
    estimator = LearnedValueEstimator(value_fn=val_fn)
    blender = HybridValueBlender(learned_estimator=estimator, config=HybridValueConfig(learned_weight=0.4, mcts_weight=0.6, blend_dynamically=True, min_visits_for_trust=5))
    node = _make_node()
    node.visits = 0
    result = blender.blend(node, mcts_value=0.5)
    assert result.source == "blended"
    assert result.effective_weight_learned > 0.4


def test_hybrid_value_blender_raw():
    def val_fn(world):
        return 0.9
    estimator = LearnedValueEstimator(value_fn=val_fn)
    blender = HybridValueBlender(learned_estimator=estimator, config=HybridValueConfig(learned_weight=0.5, mcts_weight=0.5))
    w = _make_world()
    result = blender.blend_raw(w, mcts_value=0.6)
    assert abs(result.blended_value - 0.75) < 1e-6


def test_hybrid_value_blender_log():
    estimator = LearnedValueEstimator()
    blender = HybridValueBlender(learned_estimator=estimator, utility_function=UtilityFunction())
    node = _make_node()
    blender.blend(node)
    assert len(blender.blend_log) == 1
    blender.clear_log()
    assert len(blender.blend_log) == 0


def test_dynamic_weight_adjuster():
    adjuster = DynamicWeightAdjuster()
    result = adjuster.update(mcts_estimate=0.5, learned_estimate=0.3, actual_outcome=0.4)
    assert "learned_weight" in result
    assert "mcts_weight" in result


def test_dynamic_weight_adjuster_convergence():
    adjuster = DynamicWeightAdjuster()
    for _ in range(10):
        adjuster.update(mcts_estimate=0.5, learned_estimate=0.49, actual_outcome=0.5)
    weights = adjuster.current_weights
    assert 0.0 <= weights["learned"] <= 1.0
    assert 0.0 <= weights["mcts"] <= 1.0


def test_pruning_config_defaults():
    c = PruningConfig()
    assert c.max_branching_factor == 5
    assert c.min_prior_threshold == 0.05


def test_pruning_decision_to_dict():
    d = PruningDecision(world_hash="abc", original_actions=["a", "b", "c"], pruned_actions=["c"], kept_actions=["a", "b"], reason="prior_threshold", num_pruned=1)
    result = d.to_dict()
    assert result["original_count"] == 3
    assert result["pruned_count"] == 1


def test_learned_pruning_hints_no_fn_no_priors():
    hints = LearnedPruningHints()
    w = _make_world()
    result = hints.prune_expansion(w, ["monitor", "wait", "intubation"])
    assert result == ["monitor", "wait", "intubation"]


def test_learned_pruning_hints_with_priors():
    hints = LearnedPruningHints()
    w = _make_world()
    priors = {"monitor": 0.5, "intubation": 0.4, "wait": 0.02}
    result = hints.prune_expansion(w, ["monitor", "wait", "intubation"], priors=priors)
    assert "monitor" in result
    assert "intubation" in result
    assert len(result) < 3


def test_learned_pruning_hints_custom_fn():
    def prune_fn(world, actions):
        return [a for a in actions if a != "wait"]
    hints = LearnedPruningHints(pruning_fn=prune_fn)
    w = _make_world()
    result = hints.prune_expansion(w, ["monitor", "wait", "intubation"])
    assert "wait" not in result
    assert len(result) == 2


def test_learned_pruning_hints_rollout_critical():
    hints = LearnedPruningHints()
    w = _make_world()
    w.mortality_risk = 0.8
    result = hints.prune_rollout(w, ["monitor", "wait", "intubation", "vasopressors"])
    assert "monitor" not in result
    assert "wait" not in result
    assert "intubation" in result


def test_learned_pruning_hints_rollout_stable():
    hints = LearnedPruningHints()
    w = _make_world()
    w.mortality_risk = 0.1
    result = hints.prune_rollout(w, ["monitor", "wait", "intubation"])
    assert len(result) == 3


def test_learned_pruning_hints_log():
    hints = LearnedPruningHints()
    w = _make_world()
    hints.prune_expansion(w, ["monitor"])
    assert len(hints.decision_log) == 1
    hints.clear_log()
    assert len(hints.decision_log) == 0


def test_learned_pruning_hints_total_pruned():
    def prune_fn(world, actions):
        return actions[:1]
    hints = LearnedPruningHints(pruning_fn=prune_fn)
    w = _make_world()
    hints.prune_expansion(w, ["a", "b", "c"])
    hints.prune_expansion(w, ["x", "y"])
    assert hints.total_pruned == 3


def test_hybrid_mcts_integrator_expansion():
    def prune_fn(world, actions):
        return actions[:2]
    pruning = LearnedPruningHints(pruning_fn=prune_fn)
    integrator = HybridMCTSIntegrator(pruning_hints=pruning)
    w = _make_world()
    result = integrator.get_expansion_actions(w, ["a", "b", "c", "d"])
    assert len(result) == 2
    stats = integrator.statistics
    assert stats["total_expansions"] == 1
    assert stats["expansions_pruned"] == 1


def test_hybrid_mcts_integrator_rollout():
    integrator = HybridMCTSIntegrator()
    w = _make_world()
    w.mortality_risk = 0.9
    result = integrator.get_rollout_actions(w, ["monitor", "wait", "intubation", "vasopressors"])
    assert "intubation" in result
    assert "monitor" not in result


def test_hybrid_mcts_integrator_prune_rate():
    integrator = HybridMCTSIntegrator()
    assert integrator.expansion_prune_rate == 0.0
    assert integrator.rollout_prune_rate == 0.0


def test_hybrid_mcts_integrator_reset():
    integrator = HybridMCTSIntegrator()
    w = _make_world()
    integrator.get_expansion_actions(w, ["a", "b"])
    integrator.reset_statistics()
    assert integrator.statistics["total_expansions"] == 0


def test_pruning_disabled():
    config = PruningConfig(enable_expansion_pruning=False, enable_rollout_pruning=False)
    hints = LearnedPruningHints(config=config)
    w = _make_world()
    result = hints.prune_expansion(w, ["a", "b", "c"], priors={"a": 0.9, "b": 0.01, "c": 0.01})
    assert len(result) == 3


TESTS = [
    (k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
]
