"""Snapshot models for deterministic network‑wide state capture.

The snapshots are frozen dataclasses that contain only immutable, JSON‑serialisable
information required for deterministic hash chain validation.  They are
intentionally minimal – the concrete simulation already tracks far more detail –
but they provide a stable surface for the stabilization suite and load‑balancer.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Tuple


def _hash_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Per‑hospital snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HospitalSnapshot:
    """Immutable snapshot of a single hospital's relevant state.

    * hospital_id – Deterministic identifier of the hospital.
    * total_patients – Number of patients currently under care.
    * critical_patients – Subset of patients in critical condition.
    * resources – Mapping ``resource_type -> available``.
    """
    hospital_id: str
    total_patients: int
    critical_patients: int
    resources: Dict[str, int]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Produce a deterministic ID based on a canonical string representation.
        # Sorting dict items guarantees repeatability.
        resources_str = ",".join(f"{k}:{v}" for k, v in sorted(self.resources.items()))
        text = f"{self.hospital_id}|{self.total_patients}|{self.critical_patients}|{resources_str}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


# ---------------------------------------------------------------------------
# Network‑wide snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NetworkSnapshot:
    """Immutable snapshot of the entire network at a given tick.

    * hospital_snapshots – Mapping ``hospital_id -> HospitalSnapshot``.
    * network_id – Deterministic hash of the sorted hospital IDs.
    * deterministic_id – Hash of the concatenated hospital snapshot IDs.
    """
    hospital_snapshots: Dict[str, HospitalSnapshot]
    network_id: str = field(init=False)
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic network ID – hash of sorted hospital IDs.
        sorted_ids = "|".join(sorted(self.hospital_snapshots))
        net_id = _hash_sha256(sorted_ids)
        object.__setattr__(self, "network_id", net_id)
        # Deterministic snapshot ID – hash of concatenated per‑hospital deterministic IDs.
        snapshot_ids = "|".join(self.hospital_snapshots[hid].deterministic_id for hid in sorted(self.hospital_snapshots))
        object.__setattr__(self, "deterministic_id", _hash_sha256(snapshot_ids))
