import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from scrubin.rl.env import ScrubInEnv, EnvStepResult
from scrubin.rl.action_space import ClinicalAction


@dataclass
class EpisodeTrajectory:
    seed: int
    total_reward: float
    survival: bool
    tick_count: int
    actions: List[int] = field(default_factory=list)
    rewards: List[float] = field(default_factory=list)
    observations: List[Any] = field(default_factory=list)
    infos: List[dict] = field(default_factory=list)
    mortality_curve: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "total_reward": round(self.total_reward, 6),
            "survival": self.survival,
            "tick_count": self.tick_count,
            "actions": self.actions,
            "rewards": [round(r, 6) for r in self.rewards],
            "mortality_curve": [round(m, 6) for m in self.mortality_curve],
            "num_steps": len(self.actions),
        }


@dataclass
class RolloutResult:
    episodes: List[EpisodeTrajectory]
    mean_reward: float
    mean_survival_rate: float
    mean_tick_count: float

    def to_dict(self) -> dict:
        return {
            "num_episodes": len(self.episodes),
            "mean_reward": round(self.mean_reward, 6),
            "mean_survival_rate": round(self.mean_survival_rate, 6),
            "mean_tick_count": round(self.mean_tick_count, 2),
        }


PolicyFn = Callable[[Any], ClinicalAction]


def random_policy(observation: Any) -> ClinicalAction:
    return random.choice(list(ClinicalAction))


def monitor_policy(observation: Any) -> ClinicalAction:
    return ClinicalAction.MONITOR


def wait_policy(observation: Any) -> ClinicalAction:
    return ClinicalAction.WAIT


class RolloutRunner:
    def __init__(
        self,
        env: ScrubInEnv | None = None,
        max_ticks: int = 200,
        snapshot_interval: int = 50,
    ):
        self._env = env or ScrubInEnv(
            max_ticks=max_ticks,
            snapshot_interval=snapshot_interval,
        )
        self._max_ticks = max_ticks

    def run_episode(
        self,
        policy: PolicyFn,
        seed: int | None = None,
        max_steps: int | None = None,
    ) -> EpisodeTrajectory:
        if seed is not None:
            random.seed(seed)
        obs = self._env.reset(seed=seed)
        trajectory = EpisodeTrajectory(
            seed=seed or 0,
            total_reward=0.0,
            survival=True,
            tick_count=0,
        )
        steps = max_steps or self._max_ticks
        for _ in range(steps):
            action = policy(obs)
            result = self._env.step(action)
            trajectory.actions.append(action.value)
            trajectory.rewards.append(result.reward)
            trajectory.observations.append(obs)
            trajectory.infos.append(result.info)
            world = self._env.get_world()
            if world is not None:
                trajectory.mortality_curve.append(world.mortality_risk)
            trajectory.total_reward = self._env.total_reward
            trajectory.tick_count = self._env.step_count
            obs = result.observation
            if result.terminated:
                trajectory.survival = False
                break
            if result.truncated:
                break
        return trajectory

    def run_batch(
        self,
        policy: PolicyFn,
        num_episodes: int,
        base_seed: int = 0,
        max_steps: int | None = None,
    ) -> RolloutResult:
        episodes = []
        for i in range(num_episodes):
            seed = base_seed + i
            traj = self.run_episode(policy, seed=seed, max_steps=max_steps)
            episodes.append(traj)
        rewards = [e.total_reward for e in episodes]
        survivals = [1.0 if e.survival else 0.0 for e in episodes]
        ticks = [float(e.tick_count) for e in episodes]
        return RolloutResult(
            episodes=episodes,
            mean_reward=sum(rewards) / len(rewards) if rewards else 0.0,
            mean_survival_rate=sum(survivals) / len(survivals) if survivals else 0.0,
            mean_tick_count=sum(ticks) / len(ticks) if ticks else 0.0,
        )
