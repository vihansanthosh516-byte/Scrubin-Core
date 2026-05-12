from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from scrubin.rl.env import ScrubInEnv
from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.rollout import RolloutRunner, RolloutResult, EpisodeTrajectory, PolicyFn
from scrubin.learning.policy_registry import PolicyRegistry, PolicyMetadata


@dataclass
class EvaluationResult:
    policy_id: str
    version: int
    num_episodes: int
    mean_reward: float
    mean_survival_rate: float
    mean_tick_count: float
    std_reward: float = 0.0
    min_reward: float = 0.0
    max_reward: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "num_episodes": self.num_episodes,
            "mean_reward": round(self.mean_reward, 6),
            "mean_survival_rate": round(self.mean_survival_rate, 6),
            "mean_tick_count": round(self.mean_tick_count, 2),
            "std_reward": round(self.std_reward, 6),
            "min_reward": round(self.min_reward, 6),
            "max_reward": round(self.max_reward, 6),
        }


class PolicyEvaluator:
    def __init__(
        self,
        num_episodes: int = 10,
        max_ticks: int = 50,
        base_seed: int = 0,
    ):
        self._num_episodes = num_episodes
        self._max_ticks = max_ticks
        self._base_seed = base_seed
        self._runner = RolloutRunner(max_ticks=max_ticks)

    def evaluate_policy(
        self,
        policy_fn: PolicyFn,
        policy_id: str = "unknown",
        version: int = 0,
    ) -> EvaluationResult:
        result = self._runner.run_batch(
            policy=policy_fn,
            num_episodes=self._num_episodes,
            base_seed=self._base_seed,
        )
        rewards = [e.total_reward for e in result.episodes]
        survivals = [1.0 if e.survival else 0.0 for e in result.episodes]
        ticks = [float(e.tick_count) for e in result.episodes]
        mean_r = sum(rewards) / len(rewards) if rewards else 0.0
        var = sum((r - mean_r) ** 2 for r in rewards) / len(rewards) if rewards else 0.0
        return EvaluationResult(
            policy_id=policy_id,
            version=version,
            num_episodes=self._num_episodes,
            mean_reward=mean_r,
            mean_survival_rate=sum(survivals) / len(survivals) if survivals else 0.0,
            mean_tick_count=sum(ticks) / len(ticks) if ticks else 0.0,
            std_reward=var ** 0.5,
            min_reward=min(rewards) if rewards else 0.0,
            max_reward=max(rewards) if rewards else 0.0,
        )

    def evaluate_from_registry(
        self,
        registry: PolicyRegistry,
        policy_id: str,
        version: int | None = None,
    ) -> Optional[EvaluationResult]:
        entry = registry.get(policy_id, version)
        if entry is None:
            return None
        meta, policy_fn = entry
        return self.evaluate_policy(policy_fn, policy_id=meta.policy_id, version=meta.version)

    def compare_policies(
        self,
        policies: Dict[str, PolicyFn],
    ) -> Dict[str, EvaluationResult]:
        results = {}
        for name, fn in policies.items():
            results[name] = self.evaluate_policy(fn, policy_id=name)
        return results
