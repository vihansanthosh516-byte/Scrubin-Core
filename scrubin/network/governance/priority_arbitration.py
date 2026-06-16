"""Network Priority Arbitrator – deterministic resolution of conflicting transfers.

The arbitrator orders transfer requests based on:
1. Criticality (higher ``priority`` value).
2. Shortest distance between origin and destination.
3. Arrival time (earlier ``request_time`` wins).
4. Lexicographic ``patient_id`` as final tie‑breaker.

All operations are deterministic: sorting keys are fixed and the distance
lookup uses the pre‑computed graph from ``ambulance_routing``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Any

from ..transfer_engine import TransferRequest

# ---------------------------------------------------------------------------
# Result data structure – immutable
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ArbitratedTransferPlan:
    """Immutable plan containing the approved transfer requests after arbitration."""
    approved_requests: Tuple[TransferRequest, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ID is a hash of the concatenated request IDs in order.
        concatenated = "|".join(req.deterministic_id for req in self.approved_requests)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(concatenated.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Arbitrator implementation
# ---------------------------------------------------------------------------

class NetworkPriorityArbitrator:
    """Resolves conflicting transfer decisions across hospitals deterministically.

    The ``arbitrate`` method returns an ``ArbitratedTransferPlan``.
    """

    def __init__(self) -> None:
        pass

    @staticmethod
    def _distance(origin: str, destination: str, graph: Dict[str, List[Tuple[str, int]]]) -> int:
        """Return the direct travel time in ticks from ``graph`` if present.
        If no edge exists, return a large sentinel value to de‑prioritise.
        """
        for dest, travel in graph.get(origin, []):
            if dest == destination:
                return travel
        # Fallback – treat as unreachable with high cost.
        return 10 ** 6

    def arbitrate(
        self,
        requests: List[TransferRequest],
        graph: Dict[str, List[Tuple[str, int]]],
    ) -> ArbitratedTransferPlan:
        # Sorting key follows the prescribed priority order.
        # 1. Higher ``priority`` -> sort descending (use negative for ascending sort).
        # 2. Shorter distance -> ascending.
        # 3. Earlier ``request_time`` -> ascending.
        # 4. Lexicographic ``patient_id`` -> ascending.
        sorted_requests = sorted(
            requests,
            key=lambda r: (
                -r.priority,
                self._distance(r.origin, r.destination, graph),
                r.request_time,
                r.patient_id,
            ),
        )
        # In this deterministic stub we approve all sorted requests.
        return ArbitratedTransferPlan(approved_requests=tuple(sorted_requests))
