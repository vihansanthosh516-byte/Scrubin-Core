import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from scrubin.decision.planning import PlanningState
from scrubin.decision.mcts import SearchNode
from scrubin.replay.hash import world_hash
from scrubin.world.model import SimulationWorld
from scrubin.learning.distillation import MCTSDistiller, MCTSTrace


PriorFn = Callable[[SimulationWorld], Dict[str, float]]


@dataclass
class BranchPrior:
    action: str
    prior_probability: float
    source: str = "learned"

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "prior_probability": round(self.prior_probability, 6),
            "source": self.source,
        }


@dataclass
class PriorConfig:
    prior_weight: float = 0.25
    fallback_to_uniform: bool = True
    min_prior: float = 0.01
    temperature: float = 1.0
    use_distiller: bool = True


@dataclass
class PriorIntegrationResult:
    world_hash: str
    priors: List[BranchPrior]
    applied: bool
    source: str

    def to_dict(self) -> dict:
        return {
            "world_hash": self.world_hash,
            "priors": [p.to_dict() for p in self.priors],
            "applied": self.applied,
            "source": self.source,
        }


def _softmax(scores: Dict[str, float], temperature: float = 1.0) -> Dict[str, float]:
    if not scores:
        return {}
    max_s = max(scores.values())
    exp_s = {k: math.exp((v - max_s) / temperature) for k, v in scores.items()}
    total = sum(exp_s.values())
    if total == 0:
        n = len(scores)
        return {k: 1.0 / n for k in scores}
    return {k: v / total for k, v in exp_s.items()}


class LearnedPriorProvider:
    def __init__(
        self,
        distiller: MCTSDistiller | None = None,
        custom_prior_fn: PriorFn | None = None,
        config: PriorConfig | None = None,
    ):
        self._distiller = distiller
        self._custom_prior_fn = custom_prior_fn
        self._config = config or PriorConfig()
        self._cache: Dict[str, Dict[str, float]] = {}

    def get_priors(self, world: SimulationWorld) -> Dict[str, float]:
        w_hash = world_hash(world)
        if w_hash in self._cache:
            return dict(self._cache[w_hash])
        priors = self._compute_priors(world, w_hash)
        self._cache[w_hash] = priors
        return dict(priors)

    def _compute_priors(self, world: SimulationWorld, w_hash: str) -> Dict[str, float]:
        if self._custom_prior_fn is not None:
            raw = self._custom_prior_fn(world)
            return _softmax(raw, self._config.temperature)
        if self._distiller is not None and self._config.use_distiller:
            action_priors = self._distiller.extract_priors(w_hash)
            if action_priors:
                str_priors = {}
                hierarchy = {
                    0: "monitor", 1: "oxygen_therapy", 2: "intubation",
                    3: "vasopressors", 4: "blood_transfusion", 5: "iv_fluids",
                    6: "antibiotics", 7: "central_line", 8: "bag_mask",
                    9: "ventilator_adjustment", 10: "emergency_airway",
                    11: "surgical_intervention", 12: "wait",
                }
                for action_idx, prob in action_priors.items():
                    name = hierarchy.get(action_idx, f"action_{action_idx}")
                    str_priors[name] = prob
                if str_priors:
                    return _softmax(str_priors, self._config.temperature)
        return {}

    def has_priors(self, world: SimulationWorld) -> bool:
        w_hash = world_hash(world)
        if w_hash in self._cache:
            return len(self._cache[w_hash]) > 0
        priors = self.get_priors(world)
        return len(priors) > 0

    def clear_cache(self) -> None:
        self._cache.clear()


class PriorGuidedSelector:
    def __init__(
        self,
        prior_provider: LearnedPriorProvider,
        config: PriorConfig | None = None,
    ):
        self._provider = prior_provider
        self._config = config or PriorConfig()
        self._integration_log: List[PriorIntegrationResult] = []

    def select_with_priors(
        self,
        node: SearchNode,
        exploration_constant: float = 1.414,
    ) -> SearchNode:
        if not node.children:
            return node
        priors = self._provider.get_priors(node.state.world)
        if not priors:
            return max(node.children, key=lambda c: c.uct(exploration_constant))
        scored = []
        for child in node.children:
            uct_val = child.uct(exploration_constant)
            action_name = child.action or ""
            prior_val = priors.get(action_name, self._config.min_prior)
            combined = uct_val + self._config.prior_weight * math.log(prior_val + 1e-10)
            scored.append((child, combined))
        best = max(scored, key=lambda x: x[1])
        return best[0]

    def apply_expansion_priors(
        self,
        parent: SearchNode,
        children: List[SearchNode],
    ) -> PriorIntegrationResult:
        priors = self._provider.get_priors(parent.state.world)
        w_hash = world_hash(parent.state.world)
        branch_priors = []
        applied = False
        if priors:
            for child in children:
                action_name = child.action or ""
                p = priors.get(action_name, self._config.min_prior)
                branch_priors.append(BranchPrior(
                    action=action_name,
                    prior_probability=p,
                    source="learned" if action_name in priors else "uniform_fallback",
                ))
            applied = True
        else:
            for child in children:
                branch_priors.append(BranchPrior(
                    action=child.action or "",
                    prior_probability=1.0 / len(children) if children else 0.0,
                    source="uniform",
                ))
        result = PriorIntegrationResult(
            world_hash=w_hash,
            priors=branch_priors,
            applied=applied,
            source="learned" if priors else "uniform",
        )
        self._integration_log.append(result)
        return result

    @property
    def integration_log(self) -> List[PriorIntegrationResult]:
        return list(self._integration_log)

    def clear_log(self) -> None:
        self._integration_log.clear()
