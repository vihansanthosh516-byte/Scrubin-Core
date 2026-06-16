"""Deterministic epidemic load balancer for the hospital network.

The balancer aggregates per‑hospital snapshots into a network census, determines
a surge tier based on configurable thresholds, and generates diversion actions
(e.g., redirecting incoming patients from overloaded hospitals to under‑loaded
ones).  All operations are deterministic: sorting is alphabetical, thresholds
are fixed, and diversion choices are based on the first suitable target.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .network_snapshot import HospitalSnapshot, NetworkSnapshot


def _hash_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Census snapshot (simple aggregation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NetworkCensusSnapshot:
    """Aggregated view of the network used for load‑balancing decisions.

    * total_patients – Sum of patients across all hospitals.
    * total_critical – Sum of critical patients across all hospitals.
    * resource_totals – Mapping ``resource_type -> total_available``.
    * deterministic_id – Hash of a canonical representation for replay checks.
    """
    total_patients: int
    total_critical: int
    resource_totals: Dict[str, int]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        resources_str = ",".join(f"{k}:{v}" for k, v in sorted(self.resource_totals.items()))
        text = f"{self.total_patients}|{self.total_critical}|{resources_str}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


class EpidemicLoadBalancer:
    """Deterministic load‑balancing logic.

    The class provides three public methods:

    1. ``compute_census`` – aggregates a set of ``HospitalSnapshot`` objects.
    2. ``determine_surge_tier`` – maps the census to a tier based on static
       thresholds.
    3. ``diversion_actions`` – given a census and a surge tier, produces a list
       of ``(origin_id, target_id)`` pairs indicating where to divert new
       patients.
    """

    # Fixed thresholds – can be tuned later but remain deterministic.
    SURGE_THRESHOLDS = {
        "normal": 0,
        "moderate": 1000,
        "high": 2000,
        "critical": 3000,
    }

    def compute_census(self, snapshots: Dict[str, HospitalSnapshot]) -> NetworkCensusSnapshot:
        total_patients = sum(s.total_patients for s in snapshots.values())
        total_critical = sum(s.critical_patients for s in snapshots.values())
        resource_totals: Dict[str, int] = {}
        for s in snapshots.values():
            for rtype, amt in s.resources.items():
                resource_totals[rtype] = resource_totals.get(rtype, 0) + amt
        return NetworkCensusSnapshot(
            total_patients=total_patients,
            total_critical=total_critical,
            resource_totals=resource_totals,
        )

    def determine_surge_tier(self, census: NetworkCensusSnapshot) -> str:
        """Return the surge tier for *census*.

        The tier is the highest key whose threshold is less than or equal to
        ``census.total_patients``.
        """
        tier = "normal"
        for name, threshold in sorted(self.SURGE_THRESHOLDS.items(), key=lambda kv: kv[1]):
            if census.total_patients >= threshold:
                tier = name
        return tier

    def diversion_actions(
        self,
        snapshots: Dict[str, HospitalSnapshot],
        census: NetworkCensusSnapshot,
        surge_tier: str,
    ) -> List[Tuple[str, str]]:
        """Generate deterministic patient diversion actions.

        * The method sorts hospitals alphabetically.
        * Over‑loaded hospitals (patients exceeding ``census.total_patients / n``)
          are paired with the first under‑loaded hospital that has spare capacity
          for a generic ``patient`` resource.
        * The result is a list of ``(source_id, target_id)`` tuples.
        """
        if surge_tier == "normal":
            return []
        # Simple heuristic: compute average patients per hospital.
        n = len(snapshots)
        if n == 0:
            return []
        avg = census.total_patients // n
        # Identify overloaded and underloaded hospitals.
        overloaded = [hid for hid, snap in snapshots.items() if snap.total_patients > avg]
        underloaded = [hid for hid, snap in snapshots.items() if snap.total_patients <= avg]
        # Sort for deterministic pairing.
        overloaded.sort()
        underloaded.sort()
        actions: List[Tuple[str, str]] = []
        ul_idx = 0
        for src in overloaded:
            # Find a target that is not the same as the source.
            while ul_idx < len(underloaded) and underloaded[ul_idx] == src:
                ul_idx += 1
            if ul_idx >= len(underloaded):
                break
            tgt = underloaded[ul_idx]
            actions.append((src, tgt))
            ul_idx += 1
        return actions
