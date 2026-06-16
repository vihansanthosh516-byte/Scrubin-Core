import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Iterable


def _hash_sha256(text: str) -> str:
    """Return the lower‑case hex digest of SHA‑256 for *text*.

    All deterministic IDs in the network layer are derived from this helper
    to guarantee platform‑independent results.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HospitalConfig:
    """Immutable configuration for a single hospital.

    * name – Human readable identifier.
    * region – Geographic region code (used for grouping).
    * index – Numerical index that disambiguates hospitals with the same name/region.
    * extra – Arbitrary extra configuration (JSON‑serialisable) – defaults to empty.
    """

    name: str
    region: str
    index: int = 0
    extra: dict | None = field(default_factory=dict)

    # deterministic identifiers -------------------------------------------------
    @property
    def hospital_id(self) -> str:
        """Deterministic identifier derived from ``name|region|index``.

        The algorithm is intentionally simple: a SHA‑256 hash of the
        concatenated string.  The result is a 64‑character hexadecimal string.
        """
        return _hash_sha256(f"{self.name}|{self.region}|{self.index}")

    @property
    def deterministic_id(self) -> str:
        """Secondary deterministic ID based on the primary ``hospital_id``.
        This mirrors the pattern used in other parts of the code base.
        """
        return _hash_sha256(self.hospital_id)

    # ordering helpers --------------------------------------------------------
    def __lt__(self, other: "HospitalConfig") -> bool:
        return self.hospital_id < other.hospital_id

    def __hash__(self) -> int:
        return int(self.hospital_id[:16], 16)


@dataclass(frozen=True, slots=True)
class HospitalRegistry:
    """Immutable collection of all hospital configurations in a network.

    The registry guarantees a deterministic ordering of the ``hospitals``
    tuple (alphabetical by ``hospital_id``) and provides two derived IDs:

    * ``network_id`` – hash of the concatenated ordered ``hospital_id`` values.
    * ``deterministic_id`` – hash of the ``network_id``.
    """

    hospitals: Tuple[HospitalConfig, ...]
    network_id: str = field(init=False)
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # ``object.__setattr__`` is required because the dataclass is frozen.
        sorted_hospitals = tuple(sorted(self.hospitals, key=lambda h: h.hospital_id))
        object.__setattr__(self, "hospitals", sorted_hospitals)
        network_hash_input = "|".join(h.hospital_id for h in sorted_hospitals)
        network_id = _hash_sha256(network_hash_input)
        object.__setattr__(self, "network_id", network_id)
        object.__setattr__(self, "deterministic_id", _hash_sha256(network_id))

    # convenience helpers ----------------------------------------------------
    def __len__(self) -> int:
        return len(self.hospitals)

    def __iter__(self):
        return iter(self.hospitals)

    def get_by_id(self, hospital_id: str) -> HospitalConfig | None:
        """Return the configuration matching *hospital_id* or ``None`` if missing."""
        for cfg in self.hospitals:
            if cfg.hospital_id == hospital_id:
                return cfg
        return None
