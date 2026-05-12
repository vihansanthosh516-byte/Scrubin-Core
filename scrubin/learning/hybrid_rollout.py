import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from scrubin.decision.planning import PlanningState
from scrubin.decision.policy import RolloutPolicy
from scrubin.rl.action_space import ClinicalAction, RLActionSpace
from scrubin.world.model import SimulationWorld


RolloutGuidanceFn = Callable[[SimulationWorld, List[str]], Optional[str]]


@dataclass
class HybridRolloutConfig:
    learned_weight: float = 0.6
    heuristic_weight: float = 0.3
    random_weight: float = 0.1
    fallback_to_heuristic: bool = True
    min_confidence: float = 0.3


@dataclass
class RolloutGuidanceResult:
    action: str
    source: str
    confidence: float
    world_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "source": self.source,
            "confidence": round(self.confidence, 6),
        }


class LearnedRolloutPolicy:
    def __init__(
        self,
        guidance_fn: RolloutGuidanceFn | None = None,
        config: HybridRolloutConfig | None = None,
        action_space: RLActionSpace | None = None,
    ):
        self._guidance_fn = guidance_fn
        self._config = config or HybridRolloutConfig()
        self._action_space = action_space or RLActionSpace()
        self._source_log: List[RolloutGuidanceResult] = []

    def select_action(
        self,
        world: SimulationWorld,
        available_actions: List[str],
    ) -> RolloutGuidanceResult:
        roll = random.random()
        if roll < self._config.learned_weight and self._guidance_fn is not None:
            action = self._guidance_fn(world, available_actions)
            if action is not None and action in available_actions:
                result = RolloutGuidanceResult(
                    action=action,
                    source="learned",
                    confidence=self._config.learned_weight,
                )
                self._source_log.append(result)
                return result
        heuristic_threshold = self._config.learned_weight + self._config.heuristic_weight
        if roll < heuristic_threshold:
            action = RolloutPolicy.select_action(world, available_actions)
            result = RolloutGuidanceResult(
                action=action,
                source="heuristic",
                confidence=self._config.heuristic_weight,
            )
            self._source_log.append(result)
            return result
        action = random.choice(available_actions)
        result = RolloutGuidanceResult(
            action=action,
            source="random",
            confidence=self._config.random_weight,
        )
        self._source_log.append(result)
        return result

    @property
    def source_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for r in self._source_log:
            dist[r.source] = dist.get(r.source, 0) + 1
        return dist

    @property
    def total_decisions(self) -> int:
        return len(self._source_log)

    def clear_log(self) -> None:
        self._source_log.clear()


class MortalityAwareRolloutGuidance:
    def __init__(self, action_space: RLActionSpace | None = None):
        self._action_space = action_space or RLActionSpace()

    def guide(self, world: SimulationWorld, available_actions: List[str]) -> Optional[str]:
        mortality = world.mortality_risk
        spo2 = world.physiology.vitals.get("spo2", 100)
        sys_bp = world.physiology.vitals.get("bp_systolic", 120)
        dia_bp = world.physiology.vitals.get("bp_diastolic", 80)
        map_val = (sys_bp + 2 * dia_bp) / 3.0
        if mortality > 0.7:
            if "emergency_airway" in available_actions and spo2 < 70:
                return "emergency_airway"
            if "vasopressors" in available_actions and map_val < 50:
                return "vasopressors"
            if "intubation" in available_actions:
                return "intubation"
        if spo2 < 80:
            if "intubation" in available_actions:
                return "intubation"
            if "oxygen_therapy" in available_actions:
                return "oxygen_therapy"
        if map_val < 60:
            if "vasopressors" in available_actions:
                return "vasopressors"
            if "iv_fluids" in available_actions:
                return "iv_fluids"
        return None


class AdaptiveRolloutSelector:
    def __init__(
        self,
        learned_policy: LearnedRolloutPolicy | None = None,
        config: HybridRolloutConfig | None = None,
    ):
        self._learned = learned_policy or LearnedRolloutPolicy(config=config)
        self._config = config or HybridRolloutConfig()
        self._adaptation_history: List[Dict[str, float]] = []

    def select_action(
        self,
        world: SimulationWorld,
        available_actions: List[str],
        recent_performance: float = 0.0,
    ) -> str:
        if recent_performance < -2.0:
            self._config.learned_weight = min(0.8, self._config.learned_weight + 0.05)
            self._config.heuristic_weight = max(0.1, self._config.heuristic_weight - 0.03)
            self._config.random_weight = max(0.05, self._config.random_weight - 0.02)
        elif recent_performance > 1.0:
            self._config.learned_weight = max(0.3, self._config.learned_weight - 0.03)
            self._config.heuristic_weight = min(0.5, self._config.heuristic_weight + 0.02)
        total = self._config.learned_weight + self._config.heuristic_weight + self._config.random_weight
        if total > 0:
            self._config.learned_weight /= total
            self._config.heuristic_weight /= total
            self._config.random_weight /= total
        result = self._learned.select_action(world, available_actions)
        self._adaptation_history.append({
            "learned": self._config.learned_weight,
            "heuristic": self._config.heuristic_weight,
            "random": self._config.random_weight,
        })
        return result.action

    @property
    def current_weights(self) -> Dict[str, float]:
        return {
            "learned": round(self._config.learned_weight, 6),
            "heuristic": round(self._config.heuristic_weight, 6),
            "random": round(self._config.random_weight, 6),
        }
