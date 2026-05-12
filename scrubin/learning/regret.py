import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scrubin.rl.rollout import EpisodeTrajectory, PolicyFn, RolloutRunner
from scrubin.learning.evaluation import PolicyEvaluator, EvaluationResult
from scrubin.learning.metrics import CompositeMetrics, compute_all_metrics


@dataclass
class RegretEntry:
    tick: int
    actual_reward: float
    optimal_reward: float
    regret: float
    cumulative_regret: float

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "actual_reward": round(self.actual_reward, 6),
            "optimal_reward": round(self.optimal_reward, 6),
            "regret": round(self.regret, 6),
            "cumulative_regret": round(self.cumulative_regret, 6),
        }


@dataclass
class RegretSummary:
    policy_id: str
    baseline_id: str
    num_episodes: int
    total_regret: float
    mean_regret: float
    max_regret: float
    final_cumulative_regret: float
    regret_entries: List[RegretEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "baseline_id": self.baseline_id,
            "num_episodes": self.num_episodes,
            "total_regret": round(self.total_regret, 6),
            "mean_regret": round(self.mean_regret, 6),
            "max_regret": round(self.max_regret, 6),
            "final_cumulative_regret": round(self.final_cumulative_regret, 6),
        }


@dataclass
class PolicyComparison:
    policy_a: str
    policy_b: str
    reward_delta: float
    survival_delta: float
    composite_delta: float
    regret_summary: Optional[RegretSummary] = None

    def to_dict(self) -> dict:
        d = {
            "policy_a": self.policy_a,
            "policy_b": self.policy_b,
            "reward_delta": round(self.reward_delta, 6),
            "survival_delta": round(self.survival_delta, 6),
            "composite_delta": round(self.composite_delta, 6),
        }
        if self.regret_summary is not None:
            d["regret"] = self.regret_summary.to_dict()
        return d


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


class RegretAnalyzer:
    def __init__(
        self,
        evaluator: PolicyEvaluator | None = None,
        num_episodes: int = 10,
        max_ticks: int = 50,
        base_seed: int = 0,
    ):
        self._evaluator = evaluator or PolicyEvaluator(
            num_episodes=num_episodes,
            max_ticks=max_ticks,
            base_seed=base_seed,
        )
        self._runner = RolloutRunner(max_ticks=max_ticks)

    def compute_regret(
        self,
        policy_fn: PolicyFn,
        baseline_fn: PolicyFn,
        policy_id: str = "policy",
        baseline_id: str = "baseline",
        num_episodes: int = 10,
        base_seed: int = 0,
    ) -> RegretSummary:
        policy_result = self._runner.run_batch(policy_fn, num_episodes=num_episodes, base_seed=base_seed)
        baseline_result = self._runner.run_batch(baseline_fn, num_episodes=num_episodes, base_seed=base_seed)
        entries = []
        cumulative = 0.0
        max_ticks = max(
            max(len(e.rewards) for e in policy_result.episodes) if policy_result.episodes else 0,
            max(len(e.rewards) for e in baseline_result.episodes) if baseline_result.episodes else 0,
        )
        all_regrets = []
        for tick in range(max_ticks):
            p_reward = 0.0
            b_reward = 0.0
            for ep in policy_result.episodes:
                if tick < len(ep.rewards):
                    p_reward += ep.rewards[tick]
            for ep in baseline_result.episodes:
                if tick < len(ep.rewards):
                    b_reward += ep.rewards[tick]
            p_reward /= num_episodes if num_episodes else 1
            b_reward /= num_episodes if num_episodes else 1
            regret = b_reward - p_reward
            cumulative += regret
            all_regrets.append(regret)
            entries.append(RegretEntry(
                tick=tick,
                actual_reward=p_reward,
                optimal_reward=b_reward,
                regret=regret,
                cumulative_regret=cumulative,
            ))
        total = sum(all_regrets)
        return RegretSummary(
            policy_id=policy_id,
            baseline_id=baseline_id,
            num_episodes=num_episodes,
            total_regret=round(total, 6),
            mean_regret=round(_mean(all_regrets), 6),
            max_regret=round(max(all_regrets) if all_regrets else 0.0, 6),
            final_cumulative_regret=round(cumulative, 6),
            regret_entries=entries,
        )

    def compare_policies(
        self,
        policies: Dict[str, PolicyFn],
        baseline_id: str = "baseline",
        num_episodes: int = 10,
        base_seed: int = 0,
    ) -> List[PolicyComparison]:
        if baseline_id not in policies:
            return []
        baseline_fn = policies[baseline_id]
        comparisons = []
        for pid, pfn in policies.items():
            if pid == baseline_id:
                continue
            regret = self.compute_regret(
                pfn, baseline_fn,
                policy_id=pid,
                baseline_id=baseline_id,
                num_episodes=num_episodes,
                base_seed=base_seed,
            )
            p_result = self._evaluator.evaluate_policy(pfn, policy_id=pid)
            b_result = self._evaluator.evaluate_policy(baseline_fn, policy_id=baseline_id)
            comparisons.append(PolicyComparison(
                policy_a=pid,
                policy_b=baseline_id,
                reward_delta=round(p_result.mean_reward - b_result.mean_reward, 6),
                survival_delta=round(p_result.mean_survival_rate - b_result.mean_survival_rate, 6),
                composite_delta=0.0,
                regret_summary=regret,
            ))
        return comparisons

    def simple_regret(
        self,
        policy_rewards: List[float],
        baseline_rewards: List[float],
    ) -> RegretSummary:
        n = min(len(policy_rewards), len(baseline_rewards))
        if n == 0:
            return RegretSummary(
                policy_id="policy",
                baseline_id="baseline",
                num_episodes=0,
                total_regret=0.0,
                mean_regret=0.0,
                max_regret=0.0,
                final_cumulative_regret=0.0,
            )
        entries = []
        cumulative = 0.0
        all_regrets = []
        for i in range(n):
            regret = baseline_rewards[i] - policy_rewards[i]
            cumulative += regret
            all_regrets.append(regret)
            entries.append(RegretEntry(
                tick=i,
                actual_reward=policy_rewards[i],
                optimal_reward=baseline_rewards[i],
                regret=regret,
                cumulative_regret=cumulative,
            ))
        total = sum(all_regrets)
        return RegretSummary(
            policy_id="policy",
            baseline_id="baseline",
            num_episodes=n,
            total_regret=round(total, 6),
            mean_regret=round(_mean(all_regrets), 6),
            max_regret=round(max(all_regrets), 6),
            final_cumulative_regret=round(cumulative, 6),
            regret_entries=entries,
        )
