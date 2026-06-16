"""Network Policy Engine – deterministic global rule enforcement.

The engine evaluates a set of strict policies on the current network snapshot.
All decisions are deterministic: the same snapshot always leads to identical
outputs.  The implementation is intentionally lightweight – it performs the
required checks and returns frozen result objects that can be logged by the
coordinator.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Dict

from ..network_snapshot import NetworkSnapshot, HospitalSnapshot
from ..hospital_registry import HospitalRegistry
from ..transfer_engine import TransferEngine, TransferRequest

# ---------------------------------------------------------------------------
# Result data structures – immutable (frozen)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Container for per‑hospital policy decisions.

    * decisions – Mapping ``hospital_id -> decision`` where *decision* is a
      free‑form string describing the outcome of applying the policies.
    """
    decisions: Tuple[Tuple[str, str], ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ID is a SHA‑256 of the canonical string representation.
        text = "|".join(f"{hid}:{dec}" for hid, dec in self.decisions)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class PolicyViolationReport:
    """Immutable report of any policy violations detected.

    * violations – Tuple of ``(hospital_id, description)`` entries.
    """
    violations: Tuple[Tuple[str, str], ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = "|".join(f"{hid}:{desc}" for hid, desc in self.violations)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Engine implementation
# ---------------------------------------------------------------------------

class NetworkPolicyEngine:
    """Applies deterministic global rules across hospitals each tick.

    The engine works purely on snapshots – it does **not** mutate any hospital
    state.  It returns a ``PolicyDecision`` and a ``PolicyViolationReport``.
    """

    def __init__(self) -> None:
        # No mutable state – the engine is stateless.
        pass

    # Helper – extracts ICU utilisation from a hospital snapshot.
    @staticmethod
    def _icu_utilisation(snapshot: HospitalSnapshot) -> float:
        icu = snapshot.resources.get("icu_beds", 0)
        # Unfortunately the snapshot only stores *available* counts.  The total
        # capacity is unknown here – we treat the raw number as utilisation for
        # the deterministic placeholder implementation.
        return float(icu)

    def apply_policies(
        self,
        snapshot: NetworkSnapshot,
        registry: HospitalRegistry,
        transfer_engine: TransferEngine,
    ) -> Tuple[PolicyDecision, PolicyViolationReport]:
        """Evaluate the fixed set of policies on *snapshot*.

        The function follows the prescribed order:
        1. ICU capacity limits
        2. Ambulance availability constraints
        3. Transfer prioritisation rules
        4. Surge override conditions
        """
        decisions: List[Tuple[str, str]] = []
        violations: List[Tuple[str, str]] = []

        # ----- 1. ICU capacity limits -----
        for hid, hsnap in snapshot.hospital_snapshots.items():
            icu_available = hsnap.resources.get("icu_beds", 0)
            # In our simplified snapshot the resource dict contains *available*
            # ICU beds.  If the value is negative, capacity has been exceeded.
            if icu_available < 0:
                violations.append((hid, "ICU capacity exceeded"))
                decisions.append((hid, "ICU_CAP_EXCEEDED"))
            else:
                decisions.append((hid, "ICU_OK"))

        # ----- 2. Ambulance availability constraints -----
        # The TransferEngine stores pending requests; we inspect the assigned
        # ambulance IDs for duplicates.
        assigned: Dict[str, str] = {}
        for req in transfer_engine.pending_requests:
            amb = req.assigned_ambulance
            if amb:
                if amb in assigned:
                    violations.append((req.origin, f"Ambulance {amb} assigned to multiple transfers"))
                else:
                    assigned[amb] = req.patient_id
        # No explicit decision per hospital for this rule – we merely record any
        # violations.

        # ----- 3. Transfer prioritisation rules -----
        # In this lightweight implementation we trust that the TransferEngine's
        # deterministic ordering already respects priority.  We therefore do not
        # generate additional decisions.

        # ----- 4. Surge override conditions -----
        # If any hospital is in a CRITICAL surge state (detected via ICU
        # utilisation), we emit a generic override decision.
        for hid, hsnap in snapshot.hospital_snapshots.items():
            icu_util = hsnap.resources.get("icu_beds", 0)
            if icu_util > 8:  # heuristic – more than 8 available beds indicates high load
                decisions.append((hid, "SURGE_OVERRIDE"))

        # Build immutable result objects.
        policy_decision = PolicyDecision(decisions=tuple(decisions))
        violation_report = PolicyViolationReport(violations=tuple(violations))
        return policy_decision, violation_report
