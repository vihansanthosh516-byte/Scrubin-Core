"""Hash‑Chain Validator – validates network‑level hash chain consistency.

Ensures that each recorded network hash matches a recomputed deterministic hash
derived from the current hospital snapshots (and, optionally, governance state).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Dict

from ..network_snapshot import HospitalSnapshot

# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HashChainValidationReport:
    """Immutable report describing the outcome of the hash‑chain validation.

    * valid – ``True`` if the chain matches the recomputed hashes.
    * mismatched_ticks – Tuple of tick numbers where a mismatch was found.
    """
    valid: bool
    mismatched_ticks: Tuple[int, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        ids = ",".join(str(t) for t in self.mismatched_ticks)
        text = f"{self.valid}|{ids}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Validator implementation
# ---------------------------------------------------------------------------

class HashChainValidator:
    """Validates that the recorded network hash chain matches deterministic recomputation.

    The ``validate`` method recomputes the network hash for the *current* snapshot
    using the same algorithm as ``NetworkCoordinator`` (concatenated per‑hospital
    world hashes).  It then checks the last entry of ``network_hash_chain``
    against the recomputed value.  For a more thorough implementation one would
    iterate over historic snapshots; here we provide a lightweight check.
    """

    @staticmethod
    def _compute_network_hash(snapshots: Dict[str, HospitalSnapshot]) -> str:
        # Concatenate deterministic IDs of the hospital snapshots in sorted order.
        sorted_ids = [snapshots[hid].deterministic_id for hid in sorted(snapshots)]
        combined = "|".join(sorted_ids)
        return hashlib.sha256(combined.encode()).hexdigest()

    def validate(
        self,
        network_hash_chain: List[Dict],
        snapshots: Dict[str, HospitalSnapshot],
    ) -> HashChainValidationReport:
        # Compute expected hash for the current snapshot.
        expected_hash = self._compute_network_hash(snapshots)
        mismatches: List[int] = []
        # Validate each entry against what would be expected if we recomputed at that tick.
        # Since we only have the latest snapshot, we compare only the most recent entry.
        if network_hash_chain:
            last_entry = network_hash_chain[-1]
            if last_entry.get("hash") != expected_hash:
                mismatches.append(last_entry.get("tick", len(network_hash_chain)))
        valid = len(mismatches) == 0
        return HashChainValidationReport(valid=valid, mismatched_ticks=tuple(mismatches))
