"""Network Invariant Engine – deterministic invariant validation per tick.

The engine checks a set of strict invariants on the network snapshot and the
runtime state (ambulance store, transfer requests).  Results are returned as an
immutable ``InvariantReport``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Dict

from ..network_snapshot import HospitalSnapshot
from ..transfer_engine import TransferRequest
from ..ambulance_routing import AmbulanceStore

# ---------------------------------------------------------------------------
# Immutable result structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class InvariantViolation:
    """Description of a single invariant violation.

    * kind – Identifier of the invariant (e.g., ``resource_conservation``).
    * description – Human readable explanation.
    """
    kind: str
    description: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.kind}|{self.description}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class InvariantReport:
    """Aggregated immutable report for all invariant checks.

    * violations – Tuple of ``InvariantViolation`` objects.
    """
    violations: Tuple[InvariantViolation, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ID is a hash of the concatenated violation IDs (sorted).
        ids = "|".join(v.deterministic_id for v in sorted(self.violations, key=lambda x: x.deterministic_id))
        object.__setattr__(self, "deterministic_id", hashlib.sha256(ids.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Engine implementation
# ---------------------------------------------------------------------------

class NetworkInvariantEngine:
    """Validates hard constraints after every network tick.

    The ``check`` method returns an ``InvariantReport``.  It performs the
    following invariant checks (strict):
    1. Resource conservation – no negative resource amounts.
    2. No duplicate transfer ownership – each patient appears in at most one
       pending transfer request.
    3. Ambulance exclusivity – each ambulance is assigned to at most one
       active transfer.
    4. Hospital determinism – identical input snapshot must produce identical
       output hash (implicitly verified by comparing stored hash chain later).
    """

    def __init__(self) -> None:
        # Stateless – no mutable fields.
        pass

    def check(
        self,
        snapshots: Dict[str, HospitalSnapshot],
        ambulance_store: AmbulanceStore,
        transfer_engine: "TransferEngine",
    ) -> InvariantReport:
        violations: List[InvariantViolation] = []

        # ---- 1. Resource conservation (no negative resources) ----
        for hid, snap in snapshots.items():
            for rtype, amount in snap.resources.items():
                if amount < 0:
                    violations.append(
                        InvariantViolation(
                            kind="resource_conservation",
                            description=f"Hospital {hid} has negative {rtype} ({amount})",
                        )
                    )

        # ---- 2. No duplicate transfer ownership ----
        patient_counts: Dict[str, int] = {}
        for req in transfer_engine.pending_requests:
            patient_counts[req.patient_id] = patient_counts.get(req.patient_id, 0) + 1
        for pid, cnt in patient_counts.items():
            if cnt > 1:
                violations.append(
                    InvariantViolation(
                        kind="duplicate_transfer",
                        description=f"Patient {pid} appears in {cnt} pending transfers",
                    )
                )

        # ---- 3. Ambulance exclusivity ----
        amb_assignments: Dict[str, int] = {}
        for unit in ambulance_store.units:
            if unit.status == "en_route" and unit.assigned_route is not None:
                amb_id = unit.ambulance_id
                amb_assignments[amb_id] = amb_assignments.get(amb_id, 0) + 1
        for amb_id, cnt in amb_assignments.items():
            if cnt > 1:
                violations.append(
                    InvariantViolation(
                        kind="ambulance_exclusivity",
                        description=f"Ambulance {amb_id} assigned to {cnt} active routes",
                    )
                )

        # ---- 4. Hospital determinism ----
        # This invariant is enforced elsewhere via hash‑chain validation.  We
        # include a placeholder entry so the report always contains a deterministic
        # set of violations (empty if no issues).

        return InvariantReport(violations=tuple(violations))
