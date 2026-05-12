import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.rollout import EpisodeTrajectory, PolicyFn, RolloutRunner, RolloutResult
from scrubin.rl.reward import RewardShaper, RewardConfig
from scrubin.learning.policy_registry import PolicyRegistry, PolicyMetadata, PolicyFn as RegistryPolicyFn
from scrubin.learning.evaluation import PolicyEvaluator, EvaluationResult
from scrubin.learning.metrics import compute_all_metrics, CompositeMetrics
from scrubin.world.model import SimulationWorld


SelfPlayPolicyUpdater = Callable[[PolicyFn, PolicyFn, List[EpisodeTrajectory], List[EpisodeTrajectory]], PolicyFn]


@dataclass
class SelfPlayConfig:
    num_rounds: int = 10
    max_ticks: int = 50
    base_seed: int = 0
    update_interval: int = 5
    win_threshold: float = 0.0


@dataclass
class SelfPlayRound:
    round_num: int
    policy_a_reward: float
    policy_b_reward: float
    policy_a_survival: bool
    policy_b_survival: bool
    winner: str
    seed: int

    def to_dict(self) -> dict:
        return {
            "round_num": self.round_num,
            "policy_a_reward": round(self.policy_a_reward, 6),
            "policy_b_reward": round(self.policy_b_reward, 6),
            "winner": self.winner,
            "seed": self.seed,
        }


@dataclass
class SelfPlayResult:
    num_rounds: int
    wins_a: int
    wins_b: int
    draws: int
    policy_a_id: str
    policy_b_id: str
    rounds: List[SelfPlayRound] = field(default_factory=list)
    final_policy_a_win_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "num_rounds": self.num_rounds,
            "wins_a": self.wins_a,
            "wins_b": self.wins_b,
            "draws": self.draws,
            "policy_a_id": self.policy_a_id,
            "policy_b_id": self.policy_b_id,
            "final_policy_a_win_rate": round(self.final_policy_a_win_rate, 6),
        }


@dataclass
class IterativeTrainingResult:
    num_iterations: int
    self_play_results: List[SelfPlayResult]
    policy_history: List[str]
    improvement_curve: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "num_iterations": self.num_iterations,
            "policy_history": self.policy_history,
            "improvement_curve": [round(v, 6) for v in self.improvement_curve],
            "final_win_rate": round(self.improvement_curve[-1], 6) if self.improvement_curve else 0.0,
        }


class SelfPlayRunner:
    def __init__(
        self,
        config: SelfPlayConfig | None = None,
    ):
        self._config = config or SelfPlayConfig()
        self._runner = RolloutRunner(max_ticks=self._config.max_ticks)

    def play(
        self,
        policy_a: PolicyFn,
        policy_b: PolicyFn,
        policy_a_id: str = "policy_a",
        policy_b_id: str = "policy_b",
    ) -> SelfPlayResult:
        rounds = []
        wins_a = 0
        wins_b = 0
        draws = 0
        for i in range(self._config.num_rounds):
            seed = self._config.base_seed + i
            traj_a = self._runner.run_episode(policy_a, seed=seed, max_steps=self._config.max_ticks)
            traj_b = self._runner.run_episode(policy_b, seed=seed, max_steps=self._config.max_ticks)
            if traj_a.total_reward > traj_b.total_reward + self._config.win_threshold:
                winner = policy_a_id
                wins_a += 1
            elif traj_b.total_reward > traj_a.total_reward + self._config.win_threshold:
                winner = policy_b_id
                wins_b += 1
            else:
                winner = "draw"
                draws += 1
            rounds.append(SelfPlayRound(
                round_num=i,
                policy_a_reward=traj_a.total_reward,
                policy_b_reward=traj_b.total_reward,
                policy_a_survival=traj_a.survival,
                policy_b_survival=traj_b.survival,
                winner=winner,
                seed=seed,
            ))
        total = wins_a + wins_b + draws
        win_rate = wins_a / total if total > 0 else 0.0
        return SelfPlayResult(
            num_rounds=self._config.num_rounds,
            wins_a=wins_a,
            wins_b=wins_b,
            draws=draws,
            policy_a_id=policy_a_id,
            policy_b_id=policy_b_id,
            rounds=rounds,
            final_policy_a_win_rate=win_rate,
        )

    def play_against_previous(
        self,
        current_policy: PolicyFn,
        previous_policy: PolicyFn,
        current_id: str = "current",
        previous_id: str = "previous",
    ) -> SelfPlayResult:
        return self.play(current_policy, previous_policy, policy_a_id=current_id, policy_b_id=previous_id)


class IterativeSelfPlayTrainer:
    def __init__(
        self,
        config: SelfPlayConfig | None = None,
        registry: PolicyRegistry | None = None,
        updater: SelfPlayPolicyUpdater | None = None,
    ):
        self._config = config or SelfPlayConfig()
        self._registry = registry or PolicyRegistry()
        self._updater = updater
        self._runner = SelfPlayRunner(config=self._config)

    def train(
        self,
        initial_policy: PolicyFn,
        num_iterations: int = 5,
        base_policy_id: str = "selfplay",
        initial_seed: int = 42,
    ) -> IterativeTrainingResult:
        current_policy = initial_policy
        policy_history = []
        improvement_curve = []
        self_play_results = []
        for iteration in range(num_iterations):
            version = iteration + 1
            policy_id = f"{base_policy_id}_v{version}"
            prev_version = iteration
            prev_policy_id = f"{base_policy_id}_v{prev_version}" if iteration > 0 else "baseline"
            meta = PolicyMetadata(
                policy_id=base_policy_id,
                version=version,
                training_seed=initial_seed + iteration,
                description=f"Self-play iteration {iteration + 1}",
                parent_version=prev_version if iteration > 0 else -1,
            )
            self._registry.register(meta, current_policy)
            if iteration > 0:
                prev_meta = PolicyMetadata(
                    policy_id=base_policy_id,
                    version=prev_version,
                    training_seed=initial_seed + iteration - 1,
                    description=f"Self-play iteration {iteration}",
                )
                prev_entry = self._registry.get(base_policy_id, prev_version)
                if prev_entry:
                    prev_meta, prev_fn = prev_entry
                    sp_result = self._runner.play_against_previous(
                        current_policy, prev_fn,
                        current_id=policy_id,
                        previous_id=prev_policy_id,
                    )
                    self_play_results.append(sp_result)
                    improvement_curve.append(sp_result.final_policy_a_win_rate)
            else:
                improvement_curve.append(0.5)
            policy_history.append(policy_id)
            if self._updater is not None and iteration < num_iterations - 1:
                prev_fn = self._registry.get_policy_fn(base_policy_id, prev_version) if iteration > 0 else initial_policy
                if prev_fn:
                    current_policy = self._updater(current_policy, prev_fn, [], [])
        return IterativeTrainingResult(
            num_iterations=num_iterations,
            self_play_results=self_play_results,
            policy_history=policy_history,
            improvement_curve=improvement_curve,
        )

    @property
    def registry(self) -> PolicyRegistry:
        return self._registry
