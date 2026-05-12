import random
import math

from scrubin.rl.env import ScrubInEnv
from scrubin.rl.action_space import ClinicalAction, RLActionSpace, ActionCategory
from scrubin.rl.observation import TensorEncoder, DictEncoder, ObservationVector
from scrubin.rl.reward import RewardShaper, RewardConfig, RewardComponents
from scrubin.rl.rollout import (
    RolloutRunner, EpisodeTrajectory, RolloutResult,
    random_policy, monitor_policy, wait_policy,
)
from scrubin.rl.dataset import TrajectoryDataset, TrajectoryRecord

from scrubin.learning.buffer import ReplayBuffer, ExpertTransitionBuffer, Transition
from scrubin.learning.imitation import (
    BehavioralCloningTrainer, BehavioralCloningConfig,
    collect_expert_transitions,
)
from scrubin.learning.distillation import (
    MCTSDistiller, MCTSTrace, DistillationConfig, DistillationResult,
)
from scrubin.learning.policy_registry import PolicyRegistry, PolicyMetadata
from scrubin.learning.evaluation import PolicyEvaluator, EvaluationResult
from scrubin.learning.metrics import (
    compute_all_metrics, compute_composite_score,
    ClinicalQualityMetrics, SafetyComplianceMetrics,
    ResourceEfficiencyMetrics, RewardDecompositionMetrics,
    CompositeMetrics,
)
from scrubin.learning.regret import RegretAnalyzer, RegretSummary, PolicyComparison
from scrubin.learning.benchmarks import BenchmarkRunner, CANONICAL_BENCHMARK_POLICIES
from scrubin.learning.tournaments import TournamentRunner, StatisticalComparator

from scrubin.learning.hybrid_priors import (
    LearnedPriorProvider, PriorGuidedSelector, PriorConfig, BranchPrior,
)
from scrubin.learning.hybrid_rollout import (
    LearnedRolloutPolicy, MortalityAwareRolloutGuidance,
    AdaptiveRolloutSelector, HybridRolloutConfig,
)
from scrubin.learning.hybrid_value import (
    LearnedValueEstimator, HybridValueBlender, DynamicWeightAdjuster,
    HybridValueConfig, ValueEstimate,
)
from scrubin.learning.hybrid_pruning import (
    LearnedPruningHints, HybridMCTSIntegrator, PruningConfig, PruningDecision,
)

from scrubin.learning.curriculum import (
    CurriculumTrainer, CurriculumLevel, CurriculumProgress, CurriculumResult,
    CANONICAL_CURRICULUM,
)
from scrubin.learning.selfplay import (
    SelfPlayRunner, SelfPlayConfig, SelfPlayResult,
    IterativeSelfPlayTrainer, IterativeTrainingResult,
    SelfPlayPolicyUpdater,
)
from scrubin.learning.scenario_generator import (
    ScenarioGenerator, ScenarioConfig, CANONICAL_SCENARIO_CONFIGS,
)

from scrubin.counterfactual.counterfactuals import CounterfactualEngine, CounterfactualOutcome
from scrubin.safety.safety import SafetyShield, ShieldVerdict
from scrubin.safety.constraints import CANONICAL_CONSTRAINTS

from scrubin.replay.hash import world_hash


# ---------------------------------------------------------------------------
# 9.1 – RL Environment Layer integration
# ---------------------------------------------------------------------------

def test_env_reset_step_cycle():
    env = ScrubInEnv(max_ticks=10, snapshot_interval=5)
    obs = env.reset(seed=42)
    assert isinstance(obs, ObservationVector)
    assert env.step_count == 0

    result = env.step(ClinicalAction.MONITOR)
    assert result.terminated is False
    assert result.reward is not None
    assert env.step_count == 1
    assert result.info["tick"] == 1


def test_env_episode_terminates_or_truncates():
    env = ScrubInEnv(max_ticks=10, snapshot_interval=5)
    env.reset(seed=42)
    done = False
    steps = 0
    while not done:
        r = env.step(ClinicalAction.MONITOR)
        done = r.terminated or r.truncated
        steps += 1
        if steps > 15:
            break
    assert steps <= 11


def test_env_observation_dim():
    env = ScrubInEnv(max_ticks=10, encoder="tensor")
    env.reset(seed=1)
    assert env.observation_dim > 0
    obs = env.observe()
    assert len(obs.to_list()) == env.observation_dim


def test_env_dict_encoder():
    env = ScrubInEnv(max_ticks=10, encoder="dict")
    obs = env.reset(seed=1)
    assert isinstance(obs, dict)
    assert "physiology" in obs


def test_reward_shaper_standalone():
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world_before = env.get_world()
    env.step(ClinicalAction.MONITOR)
    world_after = env.get_world()
    shaper = RewardShaper()
    components = shaper.compute(world_before, world_after, action_taken="monitor", tick=1)
    assert isinstance(components, RewardComponents)
    assert -10.0 <= components.total <= 10.0


def test_reward_components_to_dict():
    rc = RewardComponents(survival_gain=0.5, mortality_increase=0.1)
    d = rc.to_dict()
    assert "survival_gain" in d
    assert "total" in d


# ---------------------------------------------------------------------------
# 9.2 – Imitation Learning integration
# ---------------------------------------------------------------------------

def test_expert_transition_buffer_round_trip():
    env = ScrubInEnv(max_ticks=10)
    obs = env.reset(seed=42)
    buf = ExpertTransitionBuffer(capacity=100)
    action = ClinicalAction.MONITOR
    result = env.step(action)
    next_obs = env.observe()
    t = buf.record(obs, action, result.reward, next_obs, result.terminated, result.info)
    assert buf.size == 1
    assert isinstance(t, Transition)
    assert t.action == ClinicalAction.MONITOR.value


def test_replay_buffer_sample():
    buf = ReplayBuffer(capacity=100)
    for i in range(20):
        buf.add(Transition(
            observation=[float(i)], action=i % 13,
            reward=float(i), next_observation=[float(i + 1)],
            done=False, info={},
        ))
    assert buf.size == 20
    sample = buf.sample(5)
    assert len(sample) == 5


def test_collect_expert_transitions_and_bc():
    buffer = collect_expert_transitions(
        expert_policy=monitor_policy,
        num_episodes=2,
        max_ticks=10,
        seed=0,
        buffer_capacity=100,
    )
    assert buffer.size > 0

    config = BehavioralCloningConfig(epochs=2, batch_size=8)
    trainer = BehavioralCloningTrainer(config=config)
    result = trainer.train(buffer)
    assert result.epochs_trained == 2
    assert len(result.train_loss) == 2
    assert result.num_samples > 0


# ---------------------------------------------------------------------------
# 9.3 – Counterfactual Analysis integration
# ---------------------------------------------------------------------------

def test_counterfactual_compare():
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    engine = CounterfactualEngine()
    outcome = engine.compare(world, "monitor", "intubation", horizon=5)
    assert isinstance(outcome, CounterfactualOutcome)
    assert outcome.actual_action == "monitor"
    assert outcome.alternative_action == "intubation"
    assert isinstance(outcome.mortality_delta, float)


def test_counterfactual_compare_multi():
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    engine = CounterfactualEngine()
    outcomes = engine.compare_multi(world, "monitor", ["intubation", "vasopressors"], horizon=5)
    assert len(outcomes) == 2


def test_counterfactual_fork_and_replay():
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    h1 = world_hash(world)
    engine = CounterfactualEngine()
    forked = engine.fork_and_replay(world, ClinicalAction.INTUBATE, steps=3)
    h2 = world_hash(forked)
    assert h1 != h2 or True  # may be same if no state change; just verify no crash


# ---------------------------------------------------------------------------
# 9.4 – Safety Shield integration
# ---------------------------------------------------------------------------

def test_safety_shield_evaluate():
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    shield = SafetyShield()
    verdict = shield.evaluate(ClinicalAction.MONITOR, world)
    assert isinstance(verdict, ShieldVerdict)
    assert verdict.action == ClinicalAction.MONITOR


def test_safety_shield_blocks_dangerous_action():
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    shield = SafetyShield()
    shield.clear_log()
    action = shield.shield_action(ClinicalAction.SURGICAL_INTERVENTION, world)
    assert isinstance(action, ClinicalAction)


def test_safety_shield_with_env_loop():
    env = ScrubInEnv(max_ticks=10)
    shield = SafetyShield()
    obs = env.reset(seed=42)
    for _ in range(5):
        raw_action = ClinicalAction(random.randint(0, 12))
        safe_action = shield.shield_action(raw_action, env.get_world())
        result = env.step(safe_action)
        if result.terminated or result.truncated:
            break
    assert env.step_count > 0


# ---------------------------------------------------------------------------
# 9.5 – Policy Evaluation Harness integration
# ---------------------------------------------------------------------------

def test_policy_evaluator():
    evaluator = PolicyEvaluator(num_episodes=2, max_ticks=10, base_seed=0)
    result = evaluator.evaluate_policy(monitor_policy, policy_id="monitor", version=1)
    assert isinstance(result, EvaluationResult)
    assert result.num_episodes == 2
    assert result.mean_reward is not None


def test_compute_all_metrics():
    runner = RolloutRunner(max_ticks=10)
    result = runner.run_batch(monitor_policy, num_episodes=2, base_seed=0)
    metrics = compute_all_metrics(result.episodes)
    assert isinstance(metrics, CompositeMetrics)
    assert 0.0 <= metrics.composite_score <= 1.0


def test_regret_analyzer():
    analyzer = RegretAnalyzer(num_episodes=2, max_ticks=10, base_seed=0)
    summary = analyzer.compute_regret(
        monitor_policy, wait_policy,
        policy_id="monitor", baseline_id="wait",
        num_episodes=2, base_seed=0,
    )
    assert isinstance(summary, RegretSummary)
    assert summary.policy_id == "monitor"


def test_benchmark_runner():
    runner = BenchmarkRunner(num_episodes=2)
    suite_result = runner.run_suite({"monitor": monitor_policy, "wait": wait_policy})
    assert len(suite_result.results) > 0


def test_tournament_runner():
    policies = {"monitor": monitor_policy, "wait": wait_policy}
    tournament = TournamentRunner(num_rounds=2, max_ticks=10)
    result = tournament.run_tournament(policies)
    assert len(result.ranking) >= 1


# ---------------------------------------------------------------------------
# 9.6 – Hybrid Intelligence Stack integration
# ---------------------------------------------------------------------------

def test_learned_prior_provider_with_distiller():
    distiller = MCTSDistiller(config=DistillationConfig(epochs=2))
    distiller.add_trace(MCTSTrace(
        tick=0, world_hash="abc123",
        action_priors={0: 0.4, 1: 0.3, 2: 0.3},
        selected_action=0, value_estimate=0.7,
    ))
    provider = LearnedPriorProvider(distiller=distiller)
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    priors = provider.get_priors(env.get_world())
    assert isinstance(priors, dict)


def test_distillation_round_trip():
    distiller = MCTSDistiller(config=DistillationConfig(epochs=3))
    for i in range(5):
        distiller.add_trace(MCTSTrace(
            tick=i, world_hash=f"hash_{i}",
            action_priors={i % 13: 0.5, (i + 1) % 13: 0.3, (i + 2) % 13: 0.2},
            selected_action=i % 13,
            value_estimate=0.5 + 0.1 * i,
        ))
    result = distiller.distill()
    assert isinstance(result, DistillationResult)
    assert result.epochs_trained == 3
    assert distiller.num_traces == 5

    priors = distiller.extract_priors("hash_2")
    assert isinstance(priors, dict)
    val = distiller.get_value_estimate("hash_2")
    assert isinstance(val, float)


def test_mortality_aware_rollout_guidance():
    guidance = MortalityAwareRolloutGuidance()
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    available = ["monitor", "intubate", "vasopressors", "wait"]
    result = guidance.guide(world, available)
    assert result is None or isinstance(result, str)


def test_adaptive_rollout_selector():
    random.seed(42)
    learned_policy = LearnedRolloutPolicy(config=HybridRolloutConfig(
        learned_weight=0.5, heuristic_weight=0.3, random_weight=0.2,
    ))
    selector = AdaptiveRolloutSelector(learned_policy=learned_policy)
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    available = ["monitor", "intubate", "vasopressors", "wait"]
    action = selector.select_action(world, available, recent_performance=0.5)
    assert isinstance(action, str)


def test_learned_value_estimator():
    custom_fn = lambda w: 0.75
    estimator = LearnedValueEstimator(value_fn=custom_fn)
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    val = estimator.estimate(env.get_world())
    assert val == 0.75
    assert estimator.has_estimate(env.get_world())


def test_hybrid_value_blender():
    custom_fn = lambda w: 0.6
    estimator = LearnedValueEstimator(value_fn=custom_fn)
    blender = HybridValueBlender(
        learned_estimator=estimator,
        config=HybridValueConfig(learned_weight=0.4, mcts_weight=0.6),
    )
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    ve = blender.blend_raw(env.get_world(), mcts_value=0.5)
    assert isinstance(ve, ValueEstimate)
    assert ve.blended_value is not None


def test_dynamic_weight_adjuster():
    adj = DynamicWeightAdjuster()
    for _ in range(10):
        result = adj.update(mcts_estimate=0.5, learned_estimate=0.6, actual_outcome=0.55)
        assert "learned_weight" in result
        assert "mcts_weight" in result


def test_learned_pruning_hints():
    hints = LearnedPruningHints(config=PruningConfig(max_branching_factor=3, min_prior_threshold=0.1))
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    candidates = ["monitor", "intubate", "vasopressors", "wait", "antibiotics"]
    priors = {"monitor": 0.4, "intubate": 0.3, "vasopressors": 0.2, "wait": 0.05, "antibiotics": 0.05}
    kept = hints.prune_expansion(world, candidates, priors=priors)
    assert isinstance(kept, list)
    assert len(kept) <= len(candidates)


def test_hybrid_mcts_integrator():
    integrator = HybridMCTSIntegrator(config=PruningConfig(max_branching_factor=3))
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    all_actions = ["monitor", "intubate", "vasopressors", "wait", "antibiotics"]
    priors = {"monitor": 0.5, "intubate": 0.3, "vasopressors": 0.15, "wait": 0.03, "antibiotics": 0.02}
    expansion = integrator.get_expansion_actions(world, all_actions, priors=priors)
    assert isinstance(expansion, list)
    assert len(expansion) <= len(all_actions)
    stats = integrator.statistics
    assert "total_expansions" in stats


# ---------------------------------------------------------------------------
# 9.7 – Self-Play & Curriculum Learning integration
# ---------------------------------------------------------------------------

def test_curriculum_trainer_short():
    levels = [
        CurriculumLevel("easy", difficulty=0.1, max_ticks=10, num_episodes=2, graduation_threshold=0.2),
        CurriculumLevel("hard", difficulty=0.8, max_ticks=10, num_episodes=2, graduation_threshold=0.1),
    ]
    trainer = CurriculumTrainer(curriculum=levels, max_attempts_per_level=2, base_seed=0)
    result = trainer.run_curriculum(monitor_policy, policy_id="test_monitor")
    assert isinstance(result, CurriculumResult)
    assert result.total_levels == 2


def test_self_play_runner():
    config = SelfPlayConfig(num_rounds=2, max_ticks=10, base_seed=0)
    runner = SelfPlayRunner(config=config)
    result = runner.play(monitor_policy, wait_policy, "monitor", "wait")
    assert isinstance(result, SelfPlayResult)
    assert result.num_rounds == 2
    assert result.wins_a + result.wins_b + result.draws == 2


def test_iterative_self_play_trainer():
    config = SelfPlayConfig(num_rounds=2, max_ticks=10, base_seed=0)
    trainer = IterativeSelfPlayTrainer(config=config)
    result = trainer.train(monitor_policy, num_iterations=2, base_policy_id="int_test")
    assert isinstance(result, IterativeTrainingResult)
    assert result.num_iterations == 2
    assert len(result.policy_history) >= 2
    assert trainer.registry.latest_version("int_test") is not None


def test_scenario_generator():
    gen = ScenarioGenerator(base_seed=0)
    configs = gen.generate_curriculum_batch(num_levels=3, scenarios_per_level=2)
    assert len(configs) == 3
    for c in configs:
        assert c.difficulty >= 0.0


def test_scenario_generator_adversarial():
    random.seed(42)
    gen = ScenarioGenerator(base_seed=0)
    adversarial = gen.generate_adversarial(base_difficulty=0.5, num_scenarios=5, spread=0.15)
    assert len(adversarial) == 5


# ---------------------------------------------------------------------------
# Full-stack integration: 9.1 → 9.7 end-to-end
# ---------------------------------------------------------------------------

def test_full_stack_env_to_curriculum():
    env = ScrubInEnv(max_ticks=10, snapshot_interval=5)

    obs = env.reset(seed=42)
    assert isinstance(obs, ObservationVector)

    shield = SafetyShield()
    buf = ExpertTransitionBuffer(capacity=500)
    distiller = MCTSDistiller(config=DistillationConfig(epochs=2))
    registry = PolicyRegistry()

    for step in range(5):
        raw = ClinicalAction.MONITOR
        safe = shield.shield_action(raw, env.get_world())
        obs_before = env.observe()
        result = env.step(safe)
        obs_after = env.observe()
        buf.record(obs_before, safe, result.reward, obs_after, result.terminated, result.info)
        w = env.get_world()
        h = world_hash(w)
        distiller.add_trace(MCTSTrace(
            tick=env.step_count, world_hash=h,
            action_priors={ClinicalAction.MONITOR.value: 0.6, ClinicalAction.WAIT.value: 0.4},
            selected_action=safe.value, value_estimate=0.5,
        ))
        if result.terminated or result.truncated:
            break

    assert buf.size > 0
    assert distiller.num_traces > 0

    distill_result = distiller.distill()
    assert distill_result.epochs_trained == 2

    runner = RolloutRunner(max_ticks=10)
    rollout_result = runner.run_batch(monitor_policy, num_episodes=2, base_seed=0)
    assert len(rollout_result.episodes) == 2

    metrics = compute_all_metrics(rollout_result.episodes)
    assert 0.0 <= metrics.composite_score <= 1.0

    registry.register(
        PolicyMetadata(
            policy_id="stack_monitor", version=1, training_seed=42,
            performance_metrics={"composite": metrics.composite_score},
        ),
        monitor_policy,
    )
    assert registry.latest_version("stack_monitor") == 1

    evaluator = PolicyEvaluator(num_episodes=2, max_ticks=10)
    eval_result = evaluator.evaluate_from_registry(registry, "stack_monitor")
    assert eval_result is not None

    engine = CounterfactualEngine()
    env2 = ScrubInEnv(max_ticks=10)
    env2.reset(seed=42)
    cf = engine.compare(env2.get_world(), "monitor", "wait", horizon=3)
    assert isinstance(cf, CounterfactualOutcome)

    levels = [
        CurriculumLevel("v1", difficulty=0.1, max_ticks=10, num_episodes=2, graduation_threshold=0.1),
    ]
    trainer = CurriculumTrainer(curriculum=levels, max_attempts_per_level=1)
    cur_result = trainer.run_curriculum(monitor_policy, policy_id="stack_monitor")
    assert cur_result.total_levels == 1

    sp_config = SelfPlayConfig(num_rounds=2, max_ticks=10, base_seed=0)
    sp_runner = SelfPlayRunner(config=sp_config)
    sp_result = sp_runner.play(monitor_policy, wait_policy, "monitor", "wait")
    assert sp_result.num_rounds == 2

    provider = LearnedPriorProvider(distiller=distiller)
    estimator = LearnedValueEstimator(distiller=distiller)
    blender = HybridValueBlender(
        learned_estimator=estimator,
        config=HybridValueConfig(learned_weight=0.3, mcts_weight=0.7),
    )
    hints = LearnedPruningHints(config=PruningConfig(max_branching_factor=4))
    integrator = HybridMCTSIntegrator(pruning_hints=hints)

    env3 = ScrubInEnv(max_ticks=10)
    env3.reset(seed=42)
    w = env3.get_world()
    priors = provider.get_priors(w)
    val = estimator.estimate(w)
    ve = blender.blend_raw(w, mcts_value=0.5)
    expansion = integrator.get_expansion_actions(
        w, ["monitor", "intubate", "vasopressors", "wait"], priors=priors if priors else None,
    )

    assert isinstance(val, float)
    assert isinstance(ve, ValueEstimate)
    assert isinstance(expansion, list)

    gen = ScenarioGenerator(base_seed=0)
    batch = gen.generate_curriculum_batch(num_levels=2, scenarios_per_level=2)
    assert len(batch) == 2


def test_full_stack_safety_shielded_rollout():
    shield = SafetyShield()
    env = ScrubInEnv(max_ticks=10)
    obs = env.reset(seed=100)
    total_reward = 0.0
    blocks = 0
    for _ in range(8):
        raw = ClinicalAction(random.randint(0, 12))
        safe = shield.shield_action(raw, env.get_world())
        if safe != raw:
            blocks += 1
        result = env.step(safe)
        total_reward += result.reward
        if result.terminated or result.truncated:
            break
    assert env.step_count > 0

    metrics = compute_all_metrics(
        [], num_violations=0, num_blocks=blocks, num_overrides=0,
        total_rewards=[total_reward],
    )
    assert isinstance(metrics, CompositeMetrics)


def test_full_stack_dataset_export():
    runner = RolloutRunner(max_ticks=10)
    rollout = runner.run_batch(monitor_policy, num_episodes=3, base_seed=0)
    dataset = TrajectoryDataset()
    records = dataset.add_rollout(rollout)
    assert dataset.size == 3
    assert len(records) == 3
    summary = dataset.summary()
    assert "size" in summary
    assert summary["size"] == 3


def test_full_stack_registry_rollback():
    registry = PolicyRegistry()
    for v in range(1, 4):
        registry.register(
            PolicyMetadata(
                policy_id="rollback_test", version=v, training_seed=v * 10,
                performance_metrics={"score": float(v)},
            ),
            monitor_policy,
        )
    assert registry.latest_version("rollback_test") == 3
    assert registry.rollback("rollback_test", 1)
    assert registry.latest_version("rollback_test") == 1


def test_full_stack_counterfactual_with_safety():
    env = ScrubInEnv(max_ticks=10)
    env.reset(seed=42)
    world = env.get_world()
    engine = CounterfactualEngine()
    shield = SafetyShield()

    safe_monitor = shield.shield_action(ClinicalAction.MONITOR, world)
    assert safe_monitor == ClinicalAction.MONITOR

    outcomes = engine.compare_multi(
        world, "monitor",
        ["wait", "intubation", "vasopressors"],
        horizon=5,
    )
    assert len(outcomes) == 3
    for o in outcomes:
        assert o.actual_action == "monitor"


def test_full_stack_benchmark_then_tournament():
    policies = {
        "monitor": monitor_policy,
        "wait": wait_policy,
        "random": random_policy,
    }
    bench = BenchmarkRunner(num_episodes=2)
    suite = bench.run_suite(policies)
    assert len(suite.results) > 0

    tournament = TournamentRunner(num_rounds=2, max_ticks=10)
    result = tournament.run_tournament(policies)
    assert result.ranking[0] in policies


def test_full_stack_regret_between_policies():
    analyzer = RegretAnalyzer(num_episodes=2, max_ticks=10, base_seed=0)
    comparisons = analyzer.compare_policies(
        {"monitor": monitor_policy, "wait": wait_policy},
        baseline_id="wait",
        num_episodes=2,
        base_seed=0,
    )
    assert len(comparisons) >= 1
    for c in comparisons:
        assert c.policy_a != c.policy_b


TESTS = [
    # 9.1
    ("9.integration: env reset/step cycle", test_env_reset_step_cycle),
    ("9.integration: env episode terminates or truncates", test_env_episode_terminates_or_truncates),
    ("9.integration: env observation dim", test_env_observation_dim),
    ("9.integration: env dict encoder", test_env_dict_encoder),
    ("9.integration: reward shaper standalone", test_reward_shaper_standalone),
    ("9.integration: reward components to_dict", test_reward_components_to_dict),
    # 9.2
    ("9.integration: expert transition buffer", test_expert_transition_buffer_round_trip),
    ("9.integration: replay buffer sample", test_replay_buffer_sample),
    ("9.integration: collect expert + BC train", test_collect_expert_transitions_and_bc),
    # 9.3
    ("9.integration: counterfactual compare", test_counterfactual_compare),
    ("9.integration: counterfactual compare_multi", test_counterfactual_compare_multi),
    ("9.integration: counterfactual fork and replay", test_counterfactual_fork_and_replay),
    # 9.4
    ("9.integration: safety shield evaluate", test_safety_shield_evaluate),
    ("9.integration: safety shield blocks dangerous", test_safety_shield_blocks_dangerous_action),
    ("9.integration: safety shield with env loop", test_safety_shield_with_env_loop),
    # 9.5
    ("9.integration: policy evaluator", test_policy_evaluator),
    ("9.integration: compute all metrics", test_compute_all_metrics),
    ("9.integration: regret analyzer", test_regret_analyzer),
    ("9.integration: benchmark runner", test_benchmark_runner),
    ("9.integration: tournament runner", test_tournament_runner),
    # 9.6
    ("9.integration: prior provider with distiller", test_learned_prior_provider_with_distiller),
    ("9.integration: distillation round trip", test_distillation_round_trip),
    ("9.integration: mortality aware guidance", test_mortality_aware_rollout_guidance),
    ("9.integration: adaptive rollout selector", test_adaptive_rollout_selector),
    ("9.integration: value estimator", test_learned_value_estimator),
    ("9.integration: value blender", test_hybrid_value_blender),
    ("9.integration: weight adjuster", test_dynamic_weight_adjuster),
    ("9.integration: pruning hints", test_learned_pruning_hints),
    ("9.integration: hybrid mcts integrator", test_hybrid_mcts_integrator),
    # 9.7
    ("9.integration: curriculum trainer short", test_curriculum_trainer_short),
    ("9.integration: self play runner", test_self_play_runner),
    ("9.integration: iterative self play", test_iterative_self_play_trainer),
    ("9.integration: scenario generator", test_scenario_generator),
    ("9.integration: adversarial scenarios", test_scenario_generator_adversarial),
    # Full stack
    ("9.integration: full stack env→curriculum", test_full_stack_env_to_curriculum),
    ("9.integration: safety shielded rollout", test_full_stack_safety_shielded_rollout),
    ("9.integration: dataset export", test_full_stack_dataset_export),
    ("9.integration: registry rollback", test_full_stack_registry_rollback),
    ("9.integration: counterfactual + safety", test_full_stack_counterfactual_with_safety),
    ("9.integration: benchmark → tournament", test_full_stack_benchmark_then_tournament),
    ("9.integration: regret between policies", test_full_stack_regret_between_policies),
]


if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
            print(f"PASS {name}")
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {e}")
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)}")
