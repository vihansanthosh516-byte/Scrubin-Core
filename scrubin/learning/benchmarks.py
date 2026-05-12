import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from scrubin.rl.env import ScrubInEnv
from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.rollout import EpisodeTrajectory, PolicyFn, RolloutRunner, RolloutResult, random_policy, monitor_policy, wait_policy
from scrubin.rl.reward import RewardConfig
from scrubin.learning.evaluation import PolicyEvaluator, EvaluationResult
from scrubin.learning.metrics import CompositeMetrics, compute_all_metrics


@dataclass
class BenchmarkScenario:
    scenario_id: str
    description: str
    max_ticks: int
    snapshot_interval: int = 50
    reward_config: RewardConfig | None = None
    base_seed: int = 0

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "max_ticks": self.max_ticks,
            "snapshot_interval": self.snapshot_interval,
            "base_seed": self.base_seed,
        }


@dataclass
class BenchmarkResult:
    scenario: BenchmarkScenario
    policy_id: str
    version: int
    evaluation: EvaluationResult
    metrics: CompositeMetrics

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario.scenario_id,
            "policy_id": self.policy_id,
            "version": self.version,
            "evaluation": self.evaluation.to_dict(),
            "metrics": self.metrics.to_dict(),
        }


@dataclass
class BenchmarkSuiteResult:
    suite_name: str
    num_scenarios: int
    results: List[BenchmarkResult]
    policy_rankings: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "suite_name": self.suite_name,
            "num_scenarios": self.num_scenarios,
            "results": [r.to_dict() for r in self.results],
            "policy_rankings": {k: round(v, 6) for k, v in self.policy_rankings.items()},
        }


def _triage_policy(observation: Any) -> ClinicalAction:
    if isinstance(observation, dict):
        mortality = observation.get("mortality_risk", 0.0)
        spo2 = observation.get("vitals", {}).get("spo2", 100) if isinstance(observation.get("vitals"), dict) else 100
        if mortality > 0.5:
            return ClinicalAction.VASOPRESSORS
        if spo2 < 85:
            return ClinicalAction.OXYGEN_THERAPY
    return ClinicalAction.MONITOR


def _reactive_policy(observation: Any) -> ClinicalAction:
    if isinstance(observation, dict):
        mortality = observation.get("mortality_risk", 0.0)
        if mortality > 0.7:
            return ClinicalAction.EMERGENCY_AIRWAY
        if mortality > 0.5:
            return ClinicalAction.INTUBATE
        if mortality > 0.3:
            return ClinicalAction.VASOPRESSORS
    return ClinicalAction.MONITOR


CANONICAL_BENCHMARK_POLICIES: Dict[str, PolicyFn] = {
    "random": random_policy,
    "monitor": monitor_policy,
    "wait": wait_policy,
    "triage": _triage_policy,
    "reactive": _reactive_policy,
}


CANONICAL_SCENARIOS: List[BenchmarkScenario] = [
    BenchmarkScenario(
        scenario_id="short_episode",
        description="Short 30-tick episodes for rapid evaluation",
        max_ticks=30,
        base_seed=0,
    ),
    BenchmarkScenario(
        scenario_id="standard_episode",
        description="Standard 50-tick episodes",
        max_ticks=50,
        base_seed=100,
    ),
    BenchmarkScenario(
        scenario_id="extended_episode",
        description="Extended 100-tick episodes for long-horizon assessment",
        max_ticks=100,
        base_seed=200,
    ),
    BenchmarkScenario(
        scenario_id="stress_test",
        description="200-tick stress test for robustness",
        max_ticks=200,
        snapshot_interval=50,
        base_seed=300,
    ),
]


class BenchmarkRunner:
    def __init__(
        self,
        num_episodes: int = 10,
        scenarios: List[BenchmarkScenario] | None = None,
    ):
        self._num_episodes = num_episodes
        self._scenarios = scenarios or CANONICAL_SCENARIOS

    def run_benchmark(
        self,
        policy_fn: PolicyFn,
        policy_id: str = "unknown",
        version: int = 0,
        scenarios: List[BenchmarkScenario] | None = None,
    ) -> List[BenchmarkResult]:
        target_scenarios = scenarios or self._scenarios
        results = []
        for scenario in target_scenarios:
            env = ScrubInEnv(
                max_ticks=scenario.max_ticks,
                snapshot_interval=scenario.snapshot_interval,
                reward_config=scenario.reward_config,
            )
            runner = RolloutRunner(env=env, max_ticks=scenario.max_ticks)
            rollout = runner.run_batch(
                policy=policy_fn,
                num_episodes=self._num_episodes,
                base_seed=scenario.base_seed,
            )
            eval_result = self._compute_evaluation(rollout, policy_id, version)
            metrics = compute_all_metrics(rollout.episodes)
            results.append(BenchmarkResult(
                scenario=scenario,
                policy_id=policy_id,
                version=version,
                evaluation=eval_result,
                metrics=metrics,
            ))
        return results

    def run_suite(
        self,
        policies: Dict[str, PolicyFn],
        suite_name: str = "default",
    ) -> BenchmarkSuiteResult:
        all_results = []
        for policy_id, policy_fn in policies.items():
            results = self.run_benchmark(policy_fn, policy_id=policy_id)
            all_results.extend(results)
        rankings = self._rank_policies(all_results, list(policies.keys()))
        return BenchmarkSuiteResult(
            suite_name=suite_name,
            num_scenarios=len(self._scenarios),
            results=all_results,
            policy_rankings=rankings,
        )

    def _compute_evaluation(
        self,
        rollout: RolloutResult,
        policy_id: str,
        version: int,
    ) -> EvaluationResult:
        rewards = [e.total_reward for e in rollout.episodes]
        survivals = [1.0 if e.survival else 0.0 for e in rollout.episodes]
        ticks = [float(e.tick_count) for e in rollout.episodes]
        mean_r = sum(rewards) / len(rewards) if rewards else 0.0
        var = sum((r - mean_r) ** 2 for r in rewards) / len(rewards) if rewards else 0.0
        return EvaluationResult(
            policy_id=policy_id,
            version=version,
            num_episodes=len(rollout.episodes),
            mean_reward=mean_r,
            mean_survival_rate=sum(survivals) / len(survivals) if survivals else 0.0,
            mean_tick_count=sum(ticks) / len(ticks) if ticks else 0.0,
            std_reward=var ** 0.5,
            min_reward=min(rewards) if rewards else 0.0,
            max_reward=max(rewards) if rewards else 0.0,
        )

    def _rank_policies(
        self,
        results: List[BenchmarkResult],
        policy_ids: List[str],
    ) -> Dict[str, float]:
        scores: Dict[str, List[float]] = {pid: [] for pid in policy_ids}
        for r in results:
            if r.policy_id in scores:
                scores[r.policy_id].append(r.metrics.composite_score)
        rankings = {}
        for pid in policy_ids:
            vals = scores[pid]
            rankings[pid] = sum(vals) / len(vals) if vals else 0.0
        return rankings
