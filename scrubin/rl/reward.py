from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scrubin.world.model import SimulationWorld


@dataclass
class RewardComponents:
    survival_gain: float = 0.0
    organ_recovery: float = 0.0
    stabilization: float = 0.0
    early_intervention: float = 0.0
    fairness: float = 0.0
    mortality_increase: float = 0.0
    instability: float = 0.0
    resource_waste: float = 0.0
    overtreatment: float = 0.0
    queue_delay: float = 0.0
    staff_overload: float = 0.0
    outbreak_amplification: float = 0.0

    @property
    def total(self) -> float:
        positive = (
            self.survival_gain
            + self.organ_recovery
            + self.stabilization
            + self.early_intervention
            + self.fairness
        )
        negative = (
            self.mortality_increase
            + self.instability
            + self.resource_waste
            + self.overtreatment
            + self.queue_delay
            + self.staff_overload
            + self.outbreak_amplification
        )
        return round(positive - negative, 6)

    def to_dict(self) -> dict:
        d = {k: round(v, 6) for k, v in self.__dict__.items() if not k.startswith("_")}
        d["total"] = self.total
        return d


@dataclass
class RewardConfig:
    survival_gain_weight: float = 1.0
    organ_recovery_weight: float = 0.5
    stabilization_weight: float = 0.3
    early_intervention_weight: float = 0.2
    fairness_weight: float = 0.1
    mortality_increase_weight: float = 2.0
    instability_weight: float = 0.5
    resource_waste_weight: float = 0.3
    overtreatment_weight: float = 0.2
    queue_delay_weight: float = 0.1
    staff_overload_weight: float = 0.2
    outbreak_amplification_weight: float = 0.3
    max_reward: float = 10.0
    min_reward: float = -10.0


class RewardShaper:
    def __init__(self, config: RewardConfig | None = None):
        self.config = config or RewardConfig()

    def compute(
        self,
        world_before: SimulationWorld,
        world_after: SimulationWorld,
        action_taken: Optional[str] = None,
        tick: int = 0,
    ) -> RewardComponents:
        c = RewardComponents()
        c.survival_gain = self._survival_gain(world_before, world_after)
        c.organ_recovery = self._organ_recovery(world_before, world_after)
        c.stabilization = self._stabilization(world_after)
        c.early_intervention = self._early_intervention(world_before, world_after, tick)
        c.fairness = 0.0
        c.mortality_increase = self._mortality_increase(world_before, world_after)
        c.instability = self._instability(world_after)
        c.resource_waste = self._resource_waste(world_after)
        c.overtreatment = self._overtreatment(action_taken, world_before)
        c.queue_delay = 0.0
        c.staff_overload = self._staff_overload(world_after)
        c.outbreak_amplification = 0.0
        return self._apply_weights(c)

    def _survival_gain(self, before: SimulationWorld, after: SimulationWorld) -> float:
        delta = before.mortality_risk - after.mortality_risk
        return max(0.0, delta)

    def _organ_recovery(self, before: SimulationWorld, after: SimulationWorld) -> float:
        recovery = 0.0
        for name in ("cardiovascular", "respiratory", "renal", "neurologic", "hematologic"):
            b = getattr(before.organ_state, name, None)
            a = getattr(after.organ_state, name, None)
            if b and a:
                gain = a.health - b.health
                if gain > 0 and b.health < 0.5:
                    recovery += gain
        return recovery

    def _stabilization(self, world: SimulationWorld) -> float:
        if world.mortality_risk < 0.1 and world.instability_index < 0.2:
            return 0.1
        return 0.0

    def _early_intervention(self, before: SimulationWorld, after: SimulationWorld, tick: int) -> float:
        if tick <= 3 and before.mortality_risk > 0.2 and after.mortality_risk < before.mortality_risk:
            return 0.2
        return 0.0

    def _mortality_increase(self, before: SimulationWorld, after: SimulationWorld) -> float:
        delta = after.mortality_risk - before.mortality_risk
        return max(0.0, delta)

    def _instability(self, world: SimulationWorld) -> float:
        return min(1.0, world.instability_index)

    def _resource_waste(self, world: SimulationWorld) -> float:
        waste = 0.0
        for name, r in world.resource_manager.resources.items():
            if r.available == r.total_capacity and r.total_capacity > 0:
                waste += 0.05
        return waste

    def _overtreatment(self, action_taken: Optional[str], before: SimulationWorld) -> float:
        if action_taken in ("intubation", "vasopressors", "emergency_airway"):
            if before.mortality_risk < 0.05 and before.news2_score < 5:
                return 0.3
        return 0.0

    def _staff_overload(self, world: SimulationWorld) -> float:
        sb = world.resource_manager.resources.get("staff_bandwidth")
        if sb and sb.total_capacity > 0:
            utilization = sb.currently_used / sb.total_capacity
            if utilization > 0.9:
                return (utilization - 0.9) * 5.0
        return 0.0

    def _apply_weights(self, c: RewardComponents) -> RewardComponents:
        w = self.config
        c.survival_gain *= w.survival_gain_weight
        c.organ_recovery *= w.organ_recovery_weight
        c.stabilization *= w.stabilization_weight
        c.early_intervention *= w.early_intervention_weight
        c.fairness *= w.fairness_weight
        c.mortality_increase *= w.mortality_increase_weight
        c.instability *= w.instability_weight
        c.resource_waste *= w.resource_waste_weight
        c.overtreatment *= w.overtreatment_weight
        c.queue_delay *= w.queue_delay_weight
        c.staff_overload *= w.staff_overload_weight
        c.outbreak_amplification *= w.outbreak_amplification_weight
        total = c.total
        clamped = max(w.min_reward, min(w.max_reward, total))
        scale = clamped / total if total != 0 else 1.0
        if abs(scale - 1.0) > 1e-9:
            for attr in (
                "survival_gain", "organ_recovery", "stabilization",
                "early_intervention", "fairness", "mortality_increase",
                "instability", "resource_waste", "overtreatment",
                "queue_delay", "staff_overload", "outbreak_amplification",
            ):
                setattr(c, attr, round(getattr(c, attr) * scale, 6))
        return c
