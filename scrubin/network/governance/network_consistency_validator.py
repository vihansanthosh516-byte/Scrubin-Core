"""Network Consistency Validator – deterministic replay and state checks.

Ensures that the network‑wide simulation remains internally consistent across
ticks.  The validator checks resource conservation, transfer integrity, and the
continuity of the network hash chain recorded by ``NetworkReplayCertifier``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Dict

from ..network_snapshot import HospitalSnapshot
from ..transfer_engine import TransferRequest
from ..network_replay_certifier import NetworkReplayCertifier
from ..ambulance_routing import AmbulanceStore

# ---------------------------------------------------------------------------
# Result structures – immutable
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConsistencyViolation:
    """Immutable description of a single consistency violation."""
    kind: str
    description: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.kind}|{self.description}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class ConsistencyReport:
    """Immutable report summarising the network consistency validation results."""
    valid: bool
    violations: Tuple[ConsistencyViolation, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        concat = "|".join(v.deterministic_id for v in self.violations)
        text = f"{self.valid}|{concat}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Validator implementation
# ---------------------------------------------------------------------------

class NetworkConsistencyValidator:
    """Performs deterministic consistency checks on the network state.

    The ``validate`` method returns a ``ConsistencyReport``.  It aggregates
    violations from three categories and determines overall validity.
    """

    def __init__(self) -> None:
        self._certifier = NetworkReplayCertifier()

    # -------------------------------------------------------------------
    # Helper – resource conservation check per snapshot
    # -------------------------------------------------------------------
    @staticmethod
    def _check_resources(snapshots: Dict[str, HospitalSnapshot]) -> List[ConsistencyViolation]:
        violations: List[ConsistencyViolation] = []
        for hid, snap in snapshots.items():
            for rtype, amount in snap.resources.items():
                if amount < 0:
                    violations.append(
                        ConsistencyViolation(
                            kind="resource_negative",
                            description=f"Hospital {hid} has negative {rtype} ({amount})",
                        )
                    )
        return violations

    # -------------------------------------------------------------------
    # Helper – transfer integrity check
    # -------------------------------------------------------------------
    @staticmethod
    def _check_transfers(transfers: List[TransferRequest], ambulance_store: AmbulanceStore) -> List[ConsistencyViolation]:
        violations: List[ConsistencyViolation] = []
        # Build set of ambulance IDs for quick lookup.
        amb_ids = {unit.ambulance_id for unit in ambulance_store.units}
        for tr in transfers:
            if not tr.origin or not tr.destination:
                violations.append(
                    ConsistencyViolation(
                        kind="transfer_missing_fields",
                        description=f"Transfer {tr.deterministic_id} missing origin or destination",
                    )
                )
            if tr.assigned_ambulance and tr.assigned_ambulance not in amb_ids:
                violations.append(
                    ConsistencyViolation(
                        kind="ambulance_unknown",
                        description=f"Transfer {tr.deterministic_id} references unknown ambulance {tr.assigned_ambulance}",
                    )
                )
        return violations

    # -------------------------------------------------------------------
    # Public validation entry point
    # -------------------------------------------------------------------
    def validate(
        self,
        snapshots: Dict[str, HospitalSnapshot],
        transfers: List[TransferRequest],
        ambulance_store: AmbulanceStore,
        network_hash_chain: List[Dict],
    ) -> ConsistencyReport:
        violations: List[ConsistencyViolation] = []
        # 1. Resource conservation
        violations.extend(self._check_resources(snapshots))
        # 2. Transfer integrity
        violations.extend(self._check_transfers(transfers, ambulance_store))
        # 3. Hash‑chain continuity – reuse the certifier logic.
        # Populate the certifier with the provided chain for validation.
        self._certifier.chain = network_hash_chain
        if not self._certifier.validate_chain():
            violations.append(
                ConsistencyViolation(
                    kind="hash_chain",
                    description="Network hash chain validation failed",
                )
            )
        # Overall validity is true only when no violations were found.
        valid = len(violations) == 0
        report = ConsistencyReport(valid=valid, violations=tuple(violations))
        return report
