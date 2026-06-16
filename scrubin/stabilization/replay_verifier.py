"""Replay verifier – rebuilds simulation from event log and checks hash chain equality."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Tuple, List

from scrubin.stabilization.hash_chain_validator import build_hash_chain, HashChainEntry

@dataclass(frozen=True)
class ReplayVerificationResult:
    passed: bool
    total_ticks: int
    first_divergence_tick: int | None
    original_hash: str | None
    reconstructed_hash: str | None
    deterministic_id: str

def verify_replay(original_chain: Tuple[HashChainEntry, ...], seed: int, num_ticks: int, mode: str = "autonomous") -> ReplayVerificationResult:
    """Re‑run the simulation from scratch and compare hash chains.

    Returns a frozen result containing whether the replay matched and the first
    tick where a mismatch occurred (if any).
    """
    # Re‑run simulation to obtain a fresh chain
    reconstructed_chain = build_hash_chain(seed, num_ticks, mode=mode)
    # Compare chain hashes tick by tick
    divergence_tick: int | None = None
    original_hash_val: str | None = None
    reconstructed_hash_val: str | None = None
    for orig_entry, recon_entry in zip(original_chain, reconstructed_chain):
        if orig_entry.chain_hash != recon_entry.chain_hash:
            divergence_tick = orig_entry.tick
            original_hash_val = orig_entry.chain_hash
            reconstructed_hash_val = recon_entry.chain_hash
            break
    passed = divergence_tick is None
    deterministic_id = hashlib.sha256(f"{passed}:{num_ticks}:{divergence_tick}".encode()).hexdigest()
    return ReplayVerificationResult(
        passed=passed,
        total_ticks=num_ticks,
        first_divergence_tick=divergence_tick,
        original_hash=original_hash_val,
        reconstructed_hash=reconstructed_hash_val,
        deterministic_id=deterministic_id,
    )
