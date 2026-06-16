"""Surge Control Engine – deterministic network‑wide surge logic.

The engine calculates a deterministic ``surge_index`` from ED load, ICU load,
and transfer backlog.  The resulting ``SurgeState`` follows the mandatory state
order ``NORMAL → WARNING → CRITICAL → DIVERSION``.  A ``DiversionDirective``
expresses any network‑wide diversion actions (currently a simple list of target
hospital IDs).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, Dict

from ..network_snapshot import HospitalSnapshot

# ---------------------------------------------------------------------------
# Result data structures – immutable
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SurgeState:
    """Deterministic snapshot of the network surge condition.

    * index – Float in [0, 1] representing weighted surge intensity.
    * state – One of "NORMAL", "WARNING", "CRITICAL", "DIVERSION".
    """
    index: float
    state: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.index:.6f}|{self.state}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class DiversionDirective:
    """Immutable directive describing diversion targets for the network.

    * destinations – Tuple of hospital IDs to which incoming patients should be
      diverted.
    """
    destinations: Tuple[str, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = "|".join(self.destinations)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Engine implementation
# ---------------------------------------------------------------------------

class SurgeControlEngine:
    """Computes deterministic network‑wide surge state.

    The ``evaluate`` method returns a ``SurgeState`` and an optional
    ``DiversionDirective``.
    """

    # Simple deterministic thresholds for the four states (expressed as a fraction).
    THRESHOLDS = {
        "NORMAL": 0.0,
        "WARNING": 0.3,
        "CRITICAL": 0.6,
        "DIVERSION": 0.85,
    }

    def __init__(self) -> None:
        pass

    @staticmethod
    def _aggregate_icu_utilization(snapshots: Dict[str, HospitalSnapshot]) -> float:
        """Return the average ICU utilisation ratio across hospitals.

        The snapshot's ``resources`` dictionary stores available ICU beds.  We
        approximate utilisation as ``1 - (available / assumed_capacity)`` where
        ``assumed_capacity`` is the max of the observed values to keep the
        calculation deterministic without external configuration.
        """
        total_ratio = 0.0
        count = 0
        for snap in snapshots.values():
            icu_avail = snap.resources.get("icu_beds", 0)
            # Assume a fixed capacity of 10 beds per hospital (matches default).
            capacity = 10
            utilisation = max(0.0, 1.0 - icu_avail / capacity)
            total_ratio += utilisation
            count += 1
        return (total_ratio / count) if count else 0.0

    @staticmethod
    def _aggregate_ed_load(snapshots: Dict[str, HospitalSnapshot]) -> float:
        """Placeholder ED load – derived from total patients.

        For deterministic behaviour we treat the proportion of patients relative
        to a fixed baseline (e.g., 20 patients per hospital) as the ED load.
        """
        total_patients = sum(snap.total_patients for snap in snapshots.values())
        baseline = 20 * max(1, len(snapshots))
        return min(1.0, total_patients / baseline)

    def evaluate(
        self,
        snapshots: Dict[str, HospitalSnapshot],
        transfer_backlog: int,
    ) -> Tuple[SurgeState, DiversionDirective]:
        """Compute surge index and produce the corresponding state/directive.

        The index combines three equally‑weighted components:
        * ICU utilisation
        * ED load
        * Transfer backlog normalised to [0, 1] (by dividing by 50).
        """
        icu_util = self._aggregate_icu_utilization(snapshots)
        ed_load = self._aggregate_ed_load(snapshots)
        backlog_norm = min(1.0, transfer_backlog / 50.0)
        surge_index = (icu_util + ed_load + backlog_norm) / 3.0

        # Determine the deterministic state based on thresholds.
        state = "NORMAL"
        for candidate, threshold in sorted(self.THRESHOLDS.items(), key=lambda kv: kv[1]):
            if surge_index >= threshold:
                state = candidate
        # Build the deterministic objects.
        surge_state = SurgeState(index=surge_index, state=state)
        # For the placeholder, diversion destinations are the hospitals with the
        # lowest ICU utilisation when in DIVERSION state.
        if state == "DIVERSION":
            # Sort hospitals by available ICU beds (ascending) and pick the two
            # best‑performing ones as diversion targets.
            sorted_hids = sorted(
                snapshots.keys(),
                key=lambda hid: snapshots[hid].resources.get("icu_beds", 0),
            )
            destinations = tuple(sorted_hids[:2])
        else:
            destinations = tuple()
        directive = DiversionDirective(destinations=destinations)
        return surge_state, directive
