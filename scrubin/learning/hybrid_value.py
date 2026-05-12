import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from scrubin.decision.planning import PlanningState
from scrubin.decision.mcts import SearchNode
from scrubin.decision.utility import UtilityFunction
from scrubin.replay.hash import world_hash
from scrubin.world.model import SimulationWorld
from scrubin.learning.distillation import MCTSDistiller


ValueEstimateFn = Callable[[SimulationWorld], float]


@dataclass
class HybridValueConfig:
    learned_weight: float = 0.4
    mcts_weight: float = 0.6
    fallback_to_mcts: bool = True
    min_visits_for_trust: int = 5
    blend_dynamically: bool = True


@dataclass
class ValueEstimate:
    mcts_value: float
    learned_value: float
    blended_value: float
    effective_weight_learned: float
    source: str
    world_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "mcts_value": round(self.mcts_value, 6),
            "learned_value": round(self.learned_value, 6),
            "blended_value": round(self.blended_value, 6),
            "effective_weight_learned": round(self.effective_weight_learned, 6),
            "source": self.source,
        }


class LearnedValueEstimator:
    def __init__(
        self,
        value_fn: ValueEstimateFn | None = None,
        distiller: MCTSDistiller | None = None,
        config: HybridValueConfig | None = None,
    ):
        self._value_fn = value_fn
        self._distiller = distiller
        self._config = config or HybridValueConfig()
        self._estimate_log: List[ValueEstimate] = []

    def estimate(self, world: SimulationWorld) -> float:
        if self._value_fn is not None:
            return self._value_fn(world)
        if self._distiller is not None:
            w_hash = world_hash(world)
            return self._distiller.get_value_estimate(w_hash)
        return 0.0

    def has_estimate(self, world: SimulationWorld) -> bool:
        if self._value_fn is not None:
            return True
        if self._distiller is not None:
            w_hash = world_hash(world)
            val = self._distiller.get_value_estimate(w_hash)
            return val != 0.0
        return False


class HybridValueBlender:
    def __init__(
        self,
        learned_estimator: LearnedValueEstimator,
        utility_function: UtilityFunction | None = None,
        config: HybridValueConfig | None = None,
    ):
        self._estimator = learned_estimator
        self._utility = utility_function
        self._config = config or HybridValueConfig()
        self._blend_log: List[ValueEstimate] = []

    def blend(
        self,
        node: SearchNode,
        mcts_value: float | None = None,
    ) -> ValueEstimate:
        world = node.state.world
        w_hash = world_hash(world)
        if mcts_value is None:
            if node.visits > 0:
                mcts_val = node.value / node.visits
            elif self._utility is not None:
                mcts_val = self._utility.evaluate(world)
            else:
                mcts_val = 0.0
        else:
            mcts_val = mcts_value
        learned_val = self._estimator.estimate(world)
        has_learned = self._estimator.has_estimate(world)
        if not has_learned and self._config.fallback_to_mcts:
            result = ValueEstimate(
                mcts_value=mcts_val,
                learned_value=learned_val,
                blended_value=mcts_val,
                effective_weight_learned=0.0,
                source="mcts_fallback",
                world_hash=w_hash,
            )
            self._blend_log.append(result)
            return result
        effective_learned = self._config.learned_weight
        effective_mcts = self._config.mcts_weight
        if self._config.blend_dynamically and node.visits < self._config.min_visits_for_trust:
            effective_learned = min(0.6, effective_learned + 0.2)
            effective_mcts = max(0.4, 1.0 - effective_learned)
        total_w = effective_learned + effective_mcts
        if total_w > 0:
            effective_learned /= total_w
            effective_mcts /= total_w
        blended = effective_learned * learned_val + effective_mcts * mcts_val
        result = ValueEstimate(
            mcts_value=mcts_val,
            learned_value=learned_val,
            blended_value=blended,
            effective_weight_learned=effective_learned,
            source="blended",
            world_hash=w_hash,
        )
        self._blend_log.append(result)
        return result

    def blend_raw(
        self,
        world: SimulationWorld,
        mcts_value: float,
    ) -> ValueEstimate:
        w_hash = world_hash(world)
        learned_val = self._estimator.estimate(world)
        has_learned = self._estimator.has_estimate(world)
        if not has_learned:
            return ValueEstimate(
                mcts_value=mcts_value,
                learned_value=learned_val,
                blended_value=mcts_value,
                effective_weight_learned=0.0,
                source="mcts_fallback",
                world_hash=w_hash,
            )
        effective_learned = self._config.learned_weight
        effective_mcts = self._config.mcts_weight
        blended = effective_learned * learned_val + effective_mcts * mcts_value
        return ValueEstimate(
            mcts_value=mcts_value,
            learned_value=learned_val,
            blended_value=blended,
            effective_weight_learned=effective_learned,
            source="blended",
            world_hash=w_hash,
        )

    @property
    def blend_log(self) -> List[ValueEstimate]:
        return list(self._blend_log)

    def clear_log(self) -> None:
        self._blend_log.clear()


class DynamicWeightAdjuster:
    def __init__(
        self,
        config: HybridValueConfig | None = None,
        window_size: int = 20,
    ):
        self._config = config or HybridValueConfig()
        self._window_size = window_size
        self._mcts_errors: List[float] = []
        self._learned_errors: List[float] = []

    def update(
        self,
        mcts_estimate: float,
        learned_estimate: float,
        actual_outcome: float,
    ) -> Dict[str, float]:
        mcts_err = abs(mcts_estimate - actual_outcome)
        learned_err = abs(learned_estimate - actual_outcome)
        self._mcts_errors.append(mcts_err)
        self._learned_errors.append(learned_err)
        if len(self._mcts_errors) > self._window_size:
            self._mcts_errors.pop(0)
        if len(self._learned_errors) > self._window_size:
            self._learned_errors.pop(0)
        if len(self._mcts_errors) >= 5:
            avg_mcts = sum(self._mcts_errors) / len(self._mcts_errors)
            avg_learned = sum(self._learned_errors) / len(self._learned_errors)
            if avg_learned < avg_mcts * 0.8:
                self._config.learned_weight = min(0.7, self._config.learned_weight + 0.05)
                self._config.mcts_weight = 1.0 - self._config.learned_weight
            elif avg_mcts < avg_learned * 0.8:
                self._config.mcts_weight = min(0.8, self._config.mcts_weight + 0.05)
                self._config.learned_weight = 1.0 - self._config.mcts_weight
        return {
            "learned_weight": round(self._config.learned_weight, 6),
            "mcts_weight": round(self._config.mcts_weight, 6),
            "avg_mcts_error": round(sum(self._mcts_errors) / len(self._mcts_errors), 6) if self._mcts_errors else 0.0,
            "avg_learned_error": round(sum(self._learned_errors) / len(self._learned_errors), 6) if self._learned_errors else 0.0,
        }

    @property
    def current_weights(self) -> Dict[str, float]:
        return {
            "learned": round(self._config.learned_weight, 6),
            "mcts": round(self._config.mcts_weight, 6),
        }
