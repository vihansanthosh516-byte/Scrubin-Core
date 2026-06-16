'''Adaptive planning dataclasses – deterministic, immutable, replay‑safe.

This module defines the core immutable models used by the Phase 8.1 deterministic
adaptive planning and policy selection engine. All dataclasses are frozen, use
``slots=True`` for memory efficiency, and expose a deterministic SHA‑256 hash
derived from their field values. ``deterministic_id`` is a short identifier based
on the hash and can be used for deterministic referencing.
'''

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict, replace
from typing import Tuple, Any, Mapping


def _deterministic_hash(obj: Any) -> str:
    """Return a deterministic SHA‑256 hash for a dataclass instance.

    The object is converted to a ``dict`` via ``asdict`` (which recursively
    transforms nested dataclasses). ``json.dumps`` with ``sort_keys=True``
    guarantees a stable string representation across interpreter runs.
    """
    # ``default`` ensures non‑serialisable objects (e.g. tuples) are transformed
    # into a JSON‑compatible form. ``asdict`` already handles tuples, but we keep
    # the lambda for safety.
    data = asdict(obj)  # type: ignore[arg-type]
    # ``separators`` removes whitespace to keep the representation compact.
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Core adaptive models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AdaptiveAction:
    """A symbolic surgical action produced by the adaptive planner.

    * ``action_id`` – stable identifier (lexical, e.g. ``"obtain_exposure"``).
    * ``description`` – human‑readable description of the action.
    * ``priority`` – integer priority used for deterministic ordering.
    """

    action_id: str
    description: str
    priority: int = 0
    # No mutable defaults – all fields are immutable primitives.

    @property
    def deterministic_hash(self) -> str:
        return _deterministic_hash(self)

    @property
    def deterministic_id(self) -> str:
        # Short deterministic identifier – first 12 hex chars of the hash.
        return self.deterministic_hash[:12]


@dataclass(frozen=True, slots=True)
class PolicyCandidate:
    """A deterministic candidate produced by ``PolicySelector``.

    The tuple ordering guarantees replay‑safe selection: higher ``priority``
    outranks higher ``confidence`` which outranks lexical ``policy_id``.
    """

    policy_id: str
    priority: int
    confidence: float
    source: str = ""

    @property
    def deterministic_hash(self) -> str:
        return _deterministic_hash(self)

    @property
    def deterministic_id(self) -> str:
        return self.deterministic_hash[:12]


@dataclass(frozen=True, slots=True)
class AdaptivePlan:
    """Immutable adaptive surgical plan.

    ``actions`` is a **sorted tuple** of ``AdaptiveAction`` objects. Mutability
    is avoided by storing the actions as a tuple and providing ``replace``‑style
    helpers for updates.
    """

    plan_id: str
    actions: Tuple[AdaptiveAction, ...] = field(default_factory=tuple)
    # ``policy_candidates`` is optional – stored as a deterministic ordered tuple.
    policy_candidates: Tuple[PolicyCandidate, ...] = field(default_factory=tuple)

    @property
    def deterministic_hash(self) -> str:
        return _deterministic_hash(self)

    @property
    def deterministic_id(self) -> str:
        return self.deterministic_hash[:12]

    # Helper for immutable updates – mirrors the pattern used throughout the
    # codebase (e.g., ``OperatorCompetencyProfile``).
    def with_actions(self, actions: Tuple[AdaptiveAction, ...]) -> "AdaptivePlan":
        # Ensure deterministic ordering by priority then lexical id.
        sorted_actions = tuple(sorted(actions, key=lambda a: (a.priority, a.action_id)))
        return replace(self, actions=sorted_actions)

    def with_policy_candidates(self, candidates: Tuple[PolicyCandidate, ...]) -> "AdaptivePlan":
        # Deterministic ordering follows the ``PolicySelector`` contract.
        sorted_candidates = tuple(sorted(candidates, key=lambda c: (-c.priority, -c.confidence, c.policy_id)))
        return replace(self, policy_candidates=sorted_candidates)


@dataclass(frozen=True, slots=True)
class ContingencyPlan:
    """Immutable contingency – a fallback action sequence for a trigger.

    * ``trigger_condition`` – lexical identifier for the condition (e.g.
      ``"hemorrhage_worsens"``).
    * ``steps`` – ordered tuple of ``AdaptiveAction`` objects to execute when the
      trigger fires.
    """

    trigger_condition: str
    steps: Tuple[AdaptiveAction, ...] = field(default_factory=tuple)

    @property
    def deterministic_hash(self) -> str:
        return _deterministic_hash(self)

    @property
    def deterministic_id(self) -> str:
        return self.deterministic_hash[:12]


@dataclass(frozen=True, slots=True)
class SimulationPreview:
    """Deterministic preview of a candidate plan.

    All numeric fields are simple deterministic derivatives of the plan hash – no
    stochastic simulation is performed.
    """

    predicted_physiology: Mapping[str, Any] = field(default_factory=dict)
    complication_progression: Mapping[str, Any] = field(default_factory=dict)
    operative_delay: float = 0.0
    blood_loss_estimate: float = 0.0
    stability_estimate: float = 0.0
    confidence: float = 1.0
    plan_id: str = ""

    @property
    def deterministic_hash(self) -> str:
        return _deterministic_hash(self)

    @property
    def deterministic_id(self) -> str:
        return self.deterministic_hash[:12]


@dataclass(frozen=True, slots=True)
class AdaptiveSnapshot:
    """Top‑level immutable snapshot produced by ``AdaptiveManager``.

    The snapshot aggregates all components of the deterministic adaptive pipeline.
    ``aggregate_hash`` is a deterministic SHA‑256 derived from the hashes of the
    contained objects – useful for replay safety checks.
    """

    snapshot_id: str
    adaptive_plan: AdaptivePlan
    selected_policy_candidates: Tuple[PolicyCandidate, ...] = field(default_factory=tuple)
    ranked_actions: Tuple[AdaptiveAction, ...] = field(default_factory=tuple)
    contingency_plans: Tuple[ContingencyPlan, ...] = field(default_factory=tuple)
    simulation_preview: SimulationPreview = field(default_factory=SimulationPreview)
    aggregate_hash: str = ""

    @property
    def deterministic_hash(self) -> str:
        # ``aggregate_hash`` already captures the combined state; expose it as
        # the canonical deterministic hash for the snapshot.
        return self.aggregate_hash or _deterministic_hash(self)

    @property
    def deterministic_id(self) -> str:
        return self.deterministic_hash[:12]

    @staticmethod
    def compute_aggregate_hash(
        adaptive_plan: AdaptivePlan,
        selected_policy_candidates: Tuple[PolicyCandidate, ...],
        ranked_actions: Tuple[AdaptiveAction, ...],
        contingency_plans: Tuple[ContingencyPlan, ...],
        simulation_preview: SimulationPreview,
    ) -> str:
        """Deterministically combine component hashes.

        The order of concatenation mirrors the field order of the snapshot.
        """
        parts = [
            adaptive_plan.deterministic_hash,
            "|".join(c.deterministic_hash for c in selected_policy_candidates),
            "|".join(a.deterministic_hash for a in ranked_actions),
            "|".join(cp.deterministic_hash for cp in contingency_plans),
            simulation_preview.deterministic_hash,
        ]
        combined = "".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()

    def with_aggregate_hash(self) -> "AdaptiveSnapshot":
        agg = AdaptiveSnapshot.compute_aggregate_hash(
            self.adaptive_plan,
            self.selected_policy_candidates,
            self.ranked_actions,
            self.contingency_plans,
            self.simulation_preview,
        )
        return replace(self, aggregate_hash=agg)
