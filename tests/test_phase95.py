import math
from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.rollout import EpisodeTrajectory, RolloutRunner, random_policy, monitor_policy, wait_policy
from scrubin.rl.reward import RewardConfig
from scrubin.learning.metrics import (
    ClinicalQualityMetrics, SafetyComplianceMetrics, ResourceEfficiencyMetrics,
    RewardDecompositionMetrics, CompositeMetrics,
    compute_clinical_metrics, compute_safety_metrics, compute_resource_metrics,
    compute_reward_metrics, compute_composite_score, compute_all_metrics,
)
from scrubin.learning.regret import RegretAnalyzer, RegretEntry, RegretSummary, PolicyComparison
from scrubin.learning.benchmarks import (
    BenchmarkRunner, BenchmarkScenario, BenchmarkResult, BenchmarkSuiteResult,
    CANONICAL_BENCHMARK_POLICIES, CANONICAL_SCENARIOS,
)
from scrubin.learning.tournaments import (
    TournamentRunner, TournamentResult, TournamentStandings, MatchResult,
    StatisticalComparator, StatisticalComparison,
)


def _make_trajectories(num: int = 5, ticks: int = 10, survival: bool = True) -> list:
    trajs = []
    for i in range(num):
        t = EpisodeTrajectory(
            seed=i,
            total_reward=float(i),
            survival=survival,
            tick_count=ticks,
            actions=[ClinicalAction.MONITOR.value] * ticks,
            rewards=[0.1] * ticks,
            mortality_curve=[0.05] * ticks,
        )
        trajs.append(t)
    return trajs


def test_clinical_metrics_empty():
    m = compute_clinical_metrics([])
    assert m.survival_rate == 0.0
    assert m.mean_tick_count == 0.0


def test_clinical_metrics_all_survive():
    trajs = _make_trajectories(5, survival=True)
    m = compute_clinical_metrics(trajs)
    assert m.survival_rate == 1.0
    assert m.mean_tick_count == 10.0


def test_clinical_metrics_none_survive():
    trajs = _make_trajectories(5, survival=False)
    m = compute_clinical_metrics(trajs)
    assert m.survival_rate == 0.0


def test_clinical_metrics_to_dict():
    m = ClinicalQualityMetrics(survival_rate=0.8, mean_mortality_peak=0.3)
    d = m.to_dict()
    assert "survival_rate" in d
    assert d["survival_rate"] == 0.8


def test_safety_metrics_empty():
    m = compute_safety_metrics([])
    assert m.total_actions == 0
    assert m.safe_action_rate == 0.0


def test_safety_metrics_with_violations():
    trajs = _make_trajectories(3, ticks=10)
    m = compute_safety_metrics(trajs, num_violations=3, num_blocks=2, num_overrides=1)
    assert m.total_actions == 30
    assert m.violations == 3
    assert m.blocks == 2
    assert m.overrides == 1
    assert m.violation_rate == 0.1


def test_safety_metrics_to_dict():
    m = SafetyComplianceMetrics(total_actions=100, violations=5, safe_action_rate=0.95)
    d = m.to_dict()
    assert d["total_actions"] == 100
    assert d["safe_action_rate"] == 0.95


def test_resource_metrics_empty():
    m = compute_resource_metrics([])
    assert m.action_diversity == 0.0
    assert m.mean_actions_per_episode == 0.0


def test_resource_metrics_diversity():
    trajs = []
    for i in range(4):
        t = EpisodeTrajectory(
            seed=i, total_reward=0.0, survival=True, tick_count=5,
            actions=[ClinicalAction.MONITOR.value] * 3 + [ClinicalAction.INTUBATE.value] * 2,
            rewards=[0.0] * 5, mortality_curve=[0.0] * 5,
        )
        trajs.append(t)
    m = compute_resource_metrics(trajs)
    assert m.action_diversity > 0.0
    assert m.mean_actions_per_episode == 5.0


def test_resource_metrics_to_dict():
    m = ResourceEfficiencyMetrics(action_diversity=0.5, overtreatment_rate=0.1)
    d = m.to_dict()
    assert d["action_diversity"] == 0.5


def test_reward_metrics_empty():
    m = compute_reward_metrics([])
    assert m.mean_total == 0.0
    assert m.std_total == 0.0


def test_reward_metrics_values():
    m = compute_reward_metrics([1.0, 2.0, 3.0])
    assert m.mean_total == 2.0
    assert m.std_total > 0.0


def test_reward_metrics_to_dict():
    m = RewardDecompositionMetrics(mean_total=5.0, std_total=1.0)
    d = m.to_dict()
    assert d["mean_total"] == 5.0


def test_composite_score_survival_weight():
    clinical = ClinicalQualityMetrics(survival_rate=1.0, mean_mortality_final=0.0)
    safety = SafetyComplianceMetrics(total_actions=10, safe_action_rate=1.0)
    resource = ResourceEfficiencyMetrics(overtreatment_rate=0.0)
    reward = RewardDecompositionMetrics(mean_total=10.0)
    score = compute_composite_score(clinical, safety, resource, reward)
    assert 0.0 <= score <= 1.0
    assert score > 0.5


def test_composite_score_zero_survival():
    clinical = ClinicalQualityMetrics(survival_rate=0.0, mean_mortality_final=1.0)
    safety = SafetyComplianceMetrics(total_actions=10, safe_action_rate=0.5)
    resource = ResourceEfficiencyMetrics(overtreatment_rate=1.0)
    reward = RewardDecompositionMetrics(mean_total=-10.0)
    score = compute_composite_score(clinical, safety, resource, reward)
    assert 0.0 <= score <= 1.0
    assert score < 0.5


def test_compute_all_metrics():
    trajs = _make_trajectories(3, ticks=10, survival=True)
    m = compute_all_metrics(trajs, total_rewards=[1.0, 2.0, 3.0])
    assert isinstance(m, CompositeMetrics)
    assert m.clinical.survival_rate == 1.0
    assert m.reward.mean_total == 2.0
    assert 0.0 <= m.composite_score <= 1.0


def test_compute_all_metrics_to_dict():
    trajs = _make_trajectories(3, ticks=10, survival=True)
    m = compute_all_metrics(trajs)
    d = m.to_dict()
    assert "clinical" in d
    assert "safety" in d
    assert "resource" in d
    assert "reward" in d
    assert "composite_score" in d


def test_regret_entry_to_dict():
    e = RegretEntry(tick=0, actual_reward=1.0, optimal_reward=2.0, regret=1.0, cumulative_regret=1.0)
    d = e.to_dict()
    assert d["tick"] == 0
    assert d["regret"] == 1.0


def test_regret_summary_to_dict():
    s = RegretSummary(policy_id="p", baseline_id="b", num_episodes=5, total_regret=2.0, mean_regret=0.4, max_regret=1.0, final_cumulative_regret=2.0)
    d = s.to_dict()
    assert d["policy_id"] == "p"
    assert d["mean_regret"] == 0.4


def test_regret_analyzer_simple_regret():
    analyzer = RegretAnalyzer()
    s = analyzer.simple_regret([1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
    assert s.num_episodes == 3
    assert s.total_regret > 0.0
    assert len(s.regret_entries) == 3


def test_regret_analyzer_simple_regret_empty():
    analyzer = RegretAnalyzer()
    s = analyzer.simple_regret([], [])
    assert s.num_episodes == 0
    assert s.total_regret == 0.0


def test_regret_analyzer_simple_equal():
    analyzer = RegretAnalyzer()
    s = analyzer.simple_regret([5.0, 5.0], [5.0, 5.0])
    assert s.total_regret == 0.0


def test_policy_comparison_to_dict():
    c = PolicyComparison(policy_a="a", policy_b="b", reward_delta=1.0, survival_delta=0.1, composite_delta=0.05)
    d = c.to_dict()
    assert d["policy_a"] == "a"
    assert d["reward_delta"] == 1.0


def test_benchmark_scenario_to_dict():
    s = BenchmarkScenario(scenario_id="test", description="test scenario", max_ticks=50)
    d = s.to_dict()
    assert d["scenario_id"] == "test"
    assert d["max_ticks"] == 50


def test_canonical_scenarios():
    assert len(CANONICAL_SCENARIOS) == 4
    ids = [s.scenario_id for s in CANONICAL_SCENARIOS]
    assert "short_episode" in ids
    assert "standard_episode" in ids
    assert "extended_episode" in ids
    assert "stress_test" in ids


def test_canonical_benchmark_policies():
    assert "random" in CANONICAL_BENCHMARK_POLICIES
    assert "monitor" in CANONICAL_BENCHMARK_POLICIES
    assert "wait" in CANONICAL_BENCHMARK_POLICIES
    assert "triage" in CANONICAL_BENCHMARK_POLICIES
    assert "reactive" in CANONICAL_BENCHMARK_POLICIES


def test_benchmark_result_to_dict():
    scenario = BenchmarkScenario(scenario_id="test", description="test", max_ticks=50)
    trajs = _make_trajectories(3)
    from scrubin.learning.evaluation import EvaluationResult
    eval_r = EvaluationResult(policy_id="p", version=1, num_episodes=3, mean_reward=1.0, mean_survival_rate=1.0, mean_tick_count=10.0)
    metrics = compute_all_metrics(trajs)
    result = BenchmarkResult(scenario=scenario, policy_id="p", version=1, evaluation=eval_r, metrics=metrics)
    d = result.to_dict()
    assert d["scenario_id"] == "test"
    assert d["policy_id"] == "p"


def test_benchmark_runner_single_scenario():
    runner = BenchmarkRunner(num_episodes=2)
    scenario = BenchmarkScenario(scenario_id="quick", description="quick", max_ticks=10, base_seed=42)
    results = runner.run_benchmark(wait_policy, policy_id="wait", scenarios=[scenario])
    assert len(results) == 1
    assert results[0].policy_id == "wait"
    assert results[0].evaluation.num_episodes == 2
    assert isinstance(results[0].metrics, CompositeMetrics)


def test_benchmark_runner_suite():
    runner = BenchmarkRunner(num_episodes=2)
    short = BenchmarkScenario(scenario_id="short", description="short", max_ticks=10, base_seed=0)
    policies = {"monitor": monitor_policy, "wait": wait_policy}
    suite = runner.run_suite(policies, suite_name="test_suite")
    assert suite.suite_name == "test_suite"
    assert "monitor" in suite.policy_rankings
    assert "wait" in suite.policy_rankings


def test_match_result_to_dict():
    m = MatchResult(policy_a="a", policy_b="b", scenario_seed=0, reward_a=5.0, reward_b=3.0, survival_a=True, survival_b=False, winner="a")
    d = m.to_dict()
    assert d["winner"] == "a"
    assert d["reward_a"] == 5.0


def test_tournament_standings_to_dict():
    s = TournamentStandings(policy_id="p", wins=3, losses=1, draws=1, num_matches=5, win_rate=0.6, mean_reward=2.0)
    d = s.to_dict()
    assert d["wins"] == 3
    assert d["win_rate"] == 0.6


def test_tournament_runner_basic():
    runner = TournamentRunner(num_rounds=2, max_ticks=10, base_seed=42)
    policies = {"monitor": monitor_policy, "wait": wait_policy}
    result = runner.run_tournament(policies, tournament_id="test_tourney")
    assert result.tournament_id == "test_tourney"
    assert result.num_policies == 2
    assert result.champion in policies
    assert len(result.matches) > 0
    for pid in policies:
        assert pid in result.standings
        s = result.standings[pid]
        assert s.num_matches > 0
        assert s.wins + s.losses + s.draws == s.num_matches


def test_tournament_result_to_dict():
    runner = TournamentRunner(num_rounds=1, max_ticks=10, base_seed=42)
    policies = {"monitor": monitor_policy, "wait": wait_policy}
    result = runner.run_tournament(policies)
    d = result.to_dict()
    assert "champion" in d
    assert "standings" in d
    assert "num_matches" in d


def test_statistical_comparison_basic():
    comp = StatisticalComparator(confidence=0.95)
    result = comp.compare([1.0, 2.0, 3.0, 4.0, 5.0], [0.5, 1.0, 1.5, 2.0, 2.5], policy_a="good", policy_b="weak")
    assert result.policy_a == "good"
    assert result.mean_delta > 0.0
    assert isinstance(result.p_value, float)
    assert isinstance(result.significant, bool)


def test_statistical_comparison_equal():
    comp = StatisticalComparator(confidence=0.95)
    result = comp.compare([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])
    assert result.mean_delta == 0.0
    assert not result.significant


def test_statistical_comparison_empty():
    comp = StatisticalComparator()
    result = comp.compare([], [])
    assert result.mean_delta == 0.0
    assert not result.significant


def test_statistical_comparison_to_dict():
    c = StatisticalComparison(policy_a="a", policy_b="b", mean_delta=1.0, p_value=0.03, significant=True, effect_size=0.8)
    d = c.to_dict()
    assert d["mean_delta"] == 1.0
    assert d["significant"] is True


def test_pairwise_compare():
    comp = StatisticalComparator()
    rewards = {
        "a": [1.0, 2.0, 3.0],
        "b": [2.0, 3.0, 4.0],
        "c": [3.0, 4.0, 5.0],
    }
    results = comp.pairwise_compare(rewards)
    assert len(results) == 3  # a-b, a-c, b-c


def test_composite_metrics_default():
    m = CompositeMetrics()
    assert m.clinical.survival_rate == 0.0
    assert m.safety.total_actions == 0
    assert m.composite_score == 0.0


def test_regret_cumulative_accumulates():
    analyzer = RegretAnalyzer()
    s = analyzer.simple_regret([1.0, 1.0, 1.0], [2.0, 3.0, 4.0])
    assert s.regret_entries[0].cumulative_regret < s.regret_entries[1].cumulative_regret
    assert s.regret_entries[1].cumulative_regret < s.regret_entries[2].cumulative_regret


TESTS = [
    (k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
]
