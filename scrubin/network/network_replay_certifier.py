"""Deterministic network replay certifier – hash‑chain validation.

The certifier records a deterministic hash for the entire network after each
simulation tick.  The structure mirrors the per‑hospital ``hash_chain_validator``
logic but aggregates the per‑hospital world hashes into a single network hash.
"""

import hashlib
from dataclasses import dataclass, field
from typing import List


def _hash_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Hash chain entry model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NetworkHashChainEntry:
    """Immutable entry describing the network hash for a given tick.

    * deterministic_id – SHA‑256 hash of the concatenated entry fields.
    * network_tick – Simulation tick.
    * network_hash – Deterministic SHA‑256 hash of the combined per‑hospital hashes.
    * network_hash_algo – Name of the hash algorithm (``sha256``).
    * network_hash_trunc – ``False`` – we never truncate the hash.
    * network_hash_algo_version – Version of the hashing algorithm (currently ``1``).
    """

    deterministic_id: str
    network_tick: int
    network_hash: str
    network_hash_algo: str = "sha256"
    network_hash_trunc: bool = False
    network_hash_algo_version: int = 1

    @staticmethod
    def create(network_tick: int, network_hash: str) -> "NetworkHashChainEntry":
        # Deterministic ID is hash of the canonical string representation.
        text = f"{network_tick}|{network_hash}|sha256|False|1"
        deterministic_id = _hash_sha256(text)
        return NetworkHashChainEntry(
            deterministic_id=deterministic_id,
            network_tick=network_tick,
            network_hash=network_hash,
        )


# ---------------------------------------------------------------------------
# Certifier – records and validates the chain
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class NetworkReplayCertifier:
    """Collects ``NetworkHashChainEntry`` objects and validates continuity.

    The ``record_tick`` method generates a new entry and appends it to the
    internal chain.  ``validate_chain`` checks that each entry's ``deterministic_id``
    matches the recomputed hash and that the chain is ordered by increasing tick.
    """

    chain: List[NetworkHashChainEntry] = field(default_factory=list)

    def record_tick(self, network_tick: int, network_hash: str) -> NetworkHashChainEntry:
        entry = NetworkHashChainEntry.create(network_tick, network_hash)
        self.chain.append(entry)
        return entry

    def validate_chain(self) -> bool:
        """Return ``True`` if the chain is internally consistent.

        The validation recomputes each entry's deterministic ID and ensures that
        the ticks are strictly increasing.
        """
        prev_tick = -1
        for entry in self.chain:
            # Re‑compute deterministic ID.
            expected = NetworkHashChainEntry.create(entry.network_tick, entry.network_hash)
            if entry.deterministic_id != expected.deterministic_id:
                return False
            if entry.network_tick <= prev_tick:
                return False
            prev_tick = entry.network_tick
        return True
