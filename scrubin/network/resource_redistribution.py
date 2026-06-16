"""Deterministic resource redistribution across hospitals.

The implementation follows the Phase 6.1 specification while remaining
lightweight.  It operates on abstract ``ResourceDeficit`` and ``Surplus`` data
structures and produces a list of ``ResourceRedistributionPlan`` entries that
describe how resources should be moved to satisfy deficits.
"""

import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Tuple


def _hash_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Supporting data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ResourceDeficit:
    """Immutable record of a resource shortfall at a hospital.

    * hospital_id – Target hospital.
    * resource_type – Name of the resource (e.g., ``ventilator``).
    * amount – Positive integer describing the shortfall.
    """
    hospital_id: str
    resource_type: str
    amount: int
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "deterministic_id", _hash_sha256(f"{self.hospital_id}|{self.resource_type}|{self.amount}"))


@dataclass(frozen=True, slots=True)
class Surplus:
    """Immutable record of excess resources at a hospital.

    * hospital_id – Source hospital.
    * resources – Mapping ``resource_type -> amount`` (positive integers).
    """
    hospital_id: str
    resources: Dict[str, int]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Sort items for deterministic hashing.
        items = ",".join(f"{k}:{v}" for k, v in sorted(self.resources.items()))
        object.__setattr__(self, "deterministic_id", _hash_sha256(f"{self.hospital_id}|{items}"))


# ---------------------------------------------------------------------------
# Redistribution plan
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ResourceRedistributionPlan:
    """Immutable description of a single resource movement.

    * source_hospital – Hospital providing the resource.
    * destination_hospital – Hospital receiving the resource.
    * resource_type – Name of the resource.
    * amount – Quantity to transfer.
    """
    source_hospital: str
    destination_hospital: str
    resource_type: str
    amount: int
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.source_hospital}|{self.destination_hospital}|{self.resource_type}|{self.amount}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


# ---------------------------------------------------------------------------
# Engine – deterministic redistribution algorithm
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ResourceRedistributionEngine:
    """Computes a deterministic redistribution plan.

    The algorithm iterates over deficits in alphabetical order and allocates
    surplus from source hospitals also ordered alphabetically.
    """

    def compute_plan(
        self,
        deficits: List[ResourceDeficit],
        surpluses: List[Surplus],
    ) -> List[ResourceRedistributionPlan]:
        # Prepare mutable copies of surplus amounts.
        surplus_map: Dict[Tuple[str, str], int] = {}
        for s in surpluses:
            for rtype, amt in s.resources.items():
                surplus_map[(s.hospital_id, rtype)] = amt
        # Sort deficits for deterministic processing.
        deficits_sorted = sorted(deficits, key=lambda d: (d.hospital_id, d.resource_type))
        plans: List[ResourceRedistributionPlan] = []
        # Sort surplus sources for deterministic selection.
        surplus_keys = sorted(surplus_map.keys())  # (hospital_id, resource_type)
        for deficit in deficits_sorted:
            needed = deficit.amount
            # Find matching surplus entries (same resource type).
            for src_hosp, rtype in surplus_keys:
                if rtype != deficit.resource_type:
                    continue
                available = surplus_map.get((src_hosp, rtype), 0)
                if available <= 0:
                    continue
                transfer_amt = min(available, needed)
                if transfer_amt <= 0:
                    continue
                plans.append(
                    ResourceRedistributionPlan(
                        source_hospital=src_hosp,
                        destination_hospital=deficit.hospital_id,
                        resource_type=rtype,
                        amount=transfer_amt,
                    )
                )
                # Update mutable maps.
                surplus_map[(src_hosp, rtype)] = available - transfer_amt
                needed -= transfer_amt
                if needed == 0:
                    break
            # If deficit could not be fully satisfied we simply stop – the plan
            # reflects whatever was feasible.
        return plans
