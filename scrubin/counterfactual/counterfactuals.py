from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scrubin.world.model import SimulationWorld
from scrubin.replay.snapshots import SnapshotEngine
from scrubin.replay.hash import world_hash
from scrubin.rl.action_space import ClinicalAction, RLActionSpace


@dataclass
class CounterfactualOutcome:
    actual_action: str
    alternative_action: str
    fork_tick: int
    actual_mortality: float
    alternative_mortality: float
    actual_sofa: int
    alternative_sofa: int
    mortality_delta: float = 0.0
    organ_failure_delta: float = 0.0
    resource_cost_delta: float = 0.0
    survival_probability_delta: float = 0.0
    tick_count: int = 0

    def __post_init__(self):
        self.mortality_delta = round(self.actual_mortality - self.alternative_mortality, 6)
        self.organ_failure_delta = round(self.actual_sofa - self.alternative_sofa, 6)

    def to_dict(self) -> dict:
        return {
            "actual_action": self.actual_action,
            "alternative_action": self.alternative_action,
            "fork_tick": self.fork_tick,
            "actual_mortality": round(self.actual_mortality, 6),
            "alternative_mortality": round(self.alternative_mortality, 6),
            "mortality_delta": self.mortality_delta,
            "organ_failure_delta": self.organ_failure_delta,
            "resource_cost_delta": self.resource_cost_delta,
            "survival_probability_delta": self.survival_probability_delta,
            "tick_count": self.tick_count,
        }


class CounterfactualEngine:
    def __init__(self, action_space: RLActionSpace | None = None):
        self._action_space = action_space or RLActionSpace()

    def compare(
        self,
        world: SimulationWorld,
        actual_action: str,
        alternative_action: str,
        horizon: int = 10,
    ) -> CounterfactualOutcome:
        actual_world = SimulationWorld.from_dict(world.to_dict())
        alt_world = SimulationWorld.from_dict(world.to_dict())
        fork_tick = world.tick
        actual_mortality = actual_world.mortality_risk
        alt_mortality = alt_world.mortality_risk
        actual_sofa = actual_world.sofa_score
        alt_sofa = alt_world.sofa_score

        for _ in range(horizon):
            actual_world.evolve()
            alt_world.evolve()

        actual_final_mortality = actual_world.mortality_risk
        alt_final_mortality = alt_world.mortality_risk
        actual_final_sofa = actual_world.sofa_score
        alt_final_sofa = alt_world.sofa_score

        survival_actual = max(0.0, 1.0 - actual_final_mortality)
        survival_alt = max(0.0, 1.0 - alt_final_mortality)

        return CounterfactualOutcome(
            actual_action=actual_action,
            alternative_action=alternative_action,
            fork_tick=fork_tick,
            actual_mortality=actual_final_mortality,
            alternative_mortality=alt_final_mortality,
            actual_sofa=actual_final_sofa,
            alternative_sofa=alt_final_sofa,
            survival_probability_delta=round(survival_alt - survival_actual, 6),
            tick_count=horizon,
        )

    def compare_multi(
        self,
        world: SimulationWorld,
        actual_action: str,
        alternatives: List[str],
        horizon: int = 10,
    ) -> List[CounterfactualOutcome]:
        return [
            self.compare(world, actual_action, alt, horizon=horizon)
            for alt in alternatives
        ]

    def fork_and_replay(
        self,
        world: SimulationWorld,
        alternative_action: ClinicalAction,
        steps: int = 1,
    ) -> SimulationWorld:
        forked = SimulationWorld.from_dict(world.to_dict())
        for _ in range(steps):
            forked.evolve()
        return forked
