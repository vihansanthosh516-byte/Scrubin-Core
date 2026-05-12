from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scrubin.world.model import SimulationWorld
from scrubin.replay.hash import world_hash
from scrubin.rl.reward import RewardShaper, RewardComponents, RewardConfig


@dataclass
class RetrospectiveEvaluation:
    tick: int
    world_hash: str
    actual_mortality: float
    actual_sofa: int
    actual_reward: float
    optimal_mortality: float
    optimal_sofa: int
    optimal_reward: float
    regret: float = 0.0
    hindsight_action: str = ""

    def __post_init__(self):
        self.regret = round(self.optimal_reward - self.actual_reward, 6)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "world_hash": self.world_hash,
            "actual_mortality": round(self.actual_mortality, 6),
            "optimal_mortality": round(self.optimal_mortality, 6),
            "actual_reward": round(self.actual_reward, 6),
            "optimal_reward": round(self.optimal_reward, 6),
            "regret": self.regret,
            "hindsight_action": self.hindsight_action,
        }


class RetrospectiveAnalyzer:
    def __init__(self, reward_config: RewardConfig | None = None):
        self._reward_shaper = RewardShaper(config=reward_config)

    def evaluate_tick(
        self,
        world_before: SimulationWorld,
        world_after_actual: SimulationWorld,
        actual_action: str,
        best_alternative: str = "",
    ) -> RetrospectiveEvaluation:
        actual_components = self._reward_shaper.compute(
            world_before, world_after_actual, action_taken=actual_action, tick=world_before.tick
        )
        actual_reward = actual_components.total

        alt_world = SimulationWorld.from_dict(world_before.to_dict())
        alt_world.evolve()
        alt_components = self._reward_shaper.compute(
            world_before, alt_world, action_taken=best_alternative, tick=world_before.tick
        )
        optimal_reward = max(actual_reward, alt_components.total)

        return RetrospectiveEvaluation(
            tick=world_before.tick,
            world_hash=world_hash(world_before),
            actual_mortality=world_after_actual.mortality_risk,
            actual_sofa=world_after_actual.sofa_score,
            actual_reward=actual_reward,
            optimal_mortality=alt_world.mortality_risk,
            optimal_sofa=alt_world.sofa_score,
            optimal_reward=optimal_reward,
            hindsight_action=best_alternative,
        )

    def evaluate_trajectory(
        self,
        world_states: List[tuple[SimulationWorld, SimulationWorld, str]],
    ) -> List[RetrospectiveEvaluation]:
        results = []
        for before, after, action in world_states:
            results.append(self.evaluate_tick(before, after, action))
        return results

    def cumulative_regret(self, evaluations: List[RetrospectiveEvaluation]) -> float:
        return round(sum(e.regret for e in evaluations), 6)
