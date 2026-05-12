from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from scrubin.decision.planning import PlanningState
from scrubin.decision.mcts import SearchNode
from scrubin.replay.hash import world_hash
from scrubin.world.model import SimulationWorld


PruningHintFn = Callable[[SimulationWorld, List[str]], List[str]]


@dataclass
class PruningConfig:
    max_branching_factor: int = 5
    min_prior_threshold: float = 0.05
    enable_expansion_pruning: bool = True
    enable_rollout_pruning: bool = True
    safety_margin: float = 0.1


@dataclass
class PruningDecision:
    world_hash: str
    original_actions: List[str]
    pruned_actions: List[str]
    kept_actions: List[str]
    reason: str
    num_pruned: int

    def to_dict(self) -> dict:
        return {
            "world_hash": self.world_hash,
            "original_count": len(self.original_actions),
            "pruned_count": self.num_pruned,
            "kept_count": len(self.kept_actions),
            "reason": self.reason,
        }


class LearnedPruningHints:
    def __init__(
        self,
        pruning_fn: PruningHintFn | None = None,
        config: PruningConfig | None = None,
    ):
        self._pruning_fn = pruning_fn
        self._config = config or PruningConfig()
        self._decision_log: List[PruningDecision] = []

    def prune_expansion(
        self,
        world: SimulationWorld,
        candidate_actions: List[str],
        priors: Dict[str, float] | None = None,
    ) -> List[str]:
        if not self._config.enable_expansion_pruning:
            return candidate_actions
        w_hash = world_hash(world)
        if self._pruning_fn is not None:
            kept = self._pruning_fn(world, candidate_actions)
            pruned = [a for a in candidate_actions if a not in kept]
            decision = PruningDecision(
                world_hash=w_hash,
                original_actions=candidate_actions,
                pruned_actions=pruned,
                kept_actions=kept,
                reason="learned_policy",
                num_pruned=len(pruned),
            )
            self._decision_log.append(decision)
            return kept
        if priors is not None:
            scored = [(a, priors.get(a, 0.0)) for a in candidate_actions]
            scored.sort(key=lambda x: x[1], reverse=True)
            top_k = min(self._config.max_branching_factor, len(scored))
            threshold = self._config.min_prior_threshold
            kept = []
            for action, prior in scored[:top_k]:
                if prior >= threshold:
                    kept.append(action)
            if not kept:
                kept = [scored[0][0]] if scored else []
            pruned = [a for a in candidate_actions if a not in kept]
            decision = PruningDecision(
                world_hash=w_hash,
                original_actions=candidate_actions,
                pruned_actions=pruned,
                kept_actions=kept,
                reason="prior_threshold",
                num_pruned=len(pruned),
            )
            self._decision_log.append(decision)
            return kept
        decision = PruningDecision(
            world_hash=w_hash,
            original_actions=candidate_actions,
            pruned_actions=[],
            kept_actions=candidate_actions,
            reason="no_priors_or_fn",
            num_pruned=0,
        )
        self._decision_log.append(decision)
        return candidate_actions

    def prune_rollout(
        self,
        world: SimulationWorld,
        candidate_actions: List[str],
        mortality_risk: float | None = None,
    ) -> List[str]:
        if not self._config.enable_rollout_pruning:
            return candidate_actions
        mr = mortality_risk if mortality_risk is not None else world.mortality_risk
        if mr > 0.7:
            critical_actions = []
            for a in candidate_actions:
                if a in ("emergency_airway", "intubation", "vasopressors", "iv_fluids", "blood_transfusion"):
                    critical_actions.append(a)
            if critical_actions:
                return critical_actions
        return candidate_actions

    @property
    def decision_log(self) -> List[PruningDecision]:
        return list(self._decision_log)

    @property
    def total_pruned(self) -> int:
        return sum(d.num_pruned for d in self._decision_log)

    def clear_log(self) -> None:
        self._decision_log.clear()


class HybridMCTSIntegrator:
    def __init__(
        self,
        pruning_hints: LearnedPruningHints | None = None,
        config: PruningConfig | None = None,
    ):
        self._pruning = pruning_hints or LearnedPruningHints(config=config)
        self._config = config or PruningConfig()
        self._statistics: Dict[str, int] = {
            "expansions_pruned": 0,
            "rollouts_pruned": 0,
            "total_expansions": 0,
            "total_rollouts": 0,
        }

    def get_expansion_actions(
        self,
        world: SimulationWorld,
        all_actions: List[str],
        priors: Dict[str, float] | None = None,
    ) -> List[str]:
        self._statistics["total_expansions"] += 1
        result = self._pruning.prune_expansion(world, all_actions, priors)
        if len(result) < len(all_actions):
            self._statistics["expansions_pruned"] += 1
        return result

    def get_rollout_actions(
        self,
        world: SimulationWorld,
        all_actions: List[str],
        mortality_risk: float | None = None,
    ) -> List[str]:
        self._statistics["total_rollouts"] += 1
        result = self._pruning.prune_rollout(world, all_actions, mortality_risk)
        if len(result) < len(all_actions):
            self._statistics["rollouts_pruned"] += 1
        return result

    @property
    def statistics(self) -> Dict[str, int]:
        return dict(self._statistics)

    @property
    def expansion_prune_rate(self) -> float:
        total = self._statistics["total_expansions"]
        if total == 0:
            return 0.0
        return round(self._statistics["expansions_pruned"] / total, 6)

    @property
    def rollout_prune_rate(self) -> float:
        total = self._statistics["total_rollouts"]
        if total == 0:
            return 0.0
        return round(self._statistics["rollouts_pruned"] / total, 6)

    def reset_statistics(self) -> None:
        for k in self._statistics:
            self._statistics[k] = 0
        self._pruning.clear_log()
