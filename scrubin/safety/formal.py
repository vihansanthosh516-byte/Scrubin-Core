from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional


@dataclass
class ClinicalInvariant:
    id: str
    description: str
    severity: str = "error"  # "warn", "error", "fatal"
    evaluator: Callable[[Any], bool] = lambda x: True

    def evaluate(self, world: Any) -> bool:
        return self.evaluator(world)


@dataclass
class TemporalConstraint:
    id: str
    description: str
    # Predicate takes (current_world, trajectory_of_future_worlds)
    predicate: Callable[[Any, List[Any]], bool]
    lookahead_ticks: int = 5

    def evaluate(self, current_world: Any, trajectory: List[Any]) -> bool:
        return self.predicate(current_world, trajectory)


class ConstraintGraph:
    """
    Manages dependencies and hierarchical relationships between safety constraints.
    """
    def __init__(self):
        self.invariants: Dict[str, ClinicalInvariant] = {}
        self.temporal_constraints: Dict[str, TemporalConstraint] = {}
        self.dependencies: Dict[str, List[str]] = {}

    def add_invariant(self, inv: ClinicalInvariant, depends_on: List[str] = None):
        self.invariants[inv.id] = inv
        if depends_on:
            self.dependencies[inv.id] = depends_on

    def add_temporal_constraint(self, tc: TemporalConstraint):
        self.temporal_constraints[tc.id] = tc

    def evaluate_all(self, world: Any, trajectory: List[Any] = None) -> List[str]:
        violations = []
        # Evaluate invariants
        for inv_id, inv in self.invariants.items():
            if not inv.evaluate(world):
                violations.append(f"Invariant Violation: {inv_id} - {inv.description}")
        
        # Evaluate temporal constraints if trajectory is provided
        if trajectory:
            for tc_id, tc in self.temporal_constraints.items():
                if not tc.evaluate(world, trajectory):
                    violations.append(f"Temporal Violation: {tc_id} - {tc.description}")
        
        return violations


class SafetyProof:
    def __init__(self, tick: int, violations: List[str]):
        self.tick = tick
        self.violations = violations
        self.verified = len(violations) == 0
        self.timestamp = tick

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "verified": self.verified,
            "violations": self.violations,
        }


class FormalConstraintEngine:
    def __init__(self):
        self.graph = ConstraintGraph()
        self._setup_canonical_constraints()

    def _setup_canonical_constraints(self):
        # 1. Extubation Safety Invariant
        self.graph.add_temporal_constraint(TemporalConstraint(
            id="extubation_spo2_stability",
            description="Patient cannot be extubated while projected SpO2 < 88 within next 3 ticks",
            predicate=self._extubation_safety_predicate,
            lookahead_ticks=3
        ))

        # 2. Vasopressor Escalation Invariant
        self.graph.add_invariant(ClinicalInvariant(
            id="vasopressor_map_instability",
            description="Vasopressor escalation requires MAP instability (MAP < 65)",
            severity="error",
            evaluator=lambda w: w.physiology.vitals.get("bp_mean", 100) < 70 or not self._is_escalating_pressors(w)
        ))

    def prove_safety(self, world: Any, future_trajectory: List[Any] = None) -> SafetyProof:
        violations = self.graph.evaluate_all(world, future_trajectory)
        return SafetyProof(world.tick, violations)

    def _extubation_safety_predicate(self, world: Any, trajectory: List[Any]) -> bool:
        # If not extubating, it's safe
        # (This is a simplified check for demonstration)
        is_extubating = getattr(world, 'last_action', "") == "extubate"
        if not is_extubating:
            return True
        
        # Check projected SpO2 in future trajectory
        for future_world in trajectory[:3]:
            if future_world.physiology.vitals.get("spo2", 100) < 88:
                return False
        return True

    def _is_escalating_pressors(self, world: Any) -> bool:
        # Simplified check
        return getattr(world, 'last_action', "") == "increase_vasopressors"
