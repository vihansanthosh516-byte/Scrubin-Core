"""Mode parity verifier – checks that scientific and benchmark runs produce identical world state hashes per tick."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Tuple

from scrubin.stabilization.hash_chain_validator import HashChainEntry, build_hash_chain

@dataclass(frozen=True, slots=True)
class ParityReport:
    passed: bool
    total_ticks: int
    first_parity_failure_tick: int | None
    scientific_hash: str | None
    benchmark_hash: str | None
    deterministic_id: str

def verify_mode_parity(seed: int, num_ticks: int) -> ParityReport:
    """Run both scientific and benchmark simulations and compare world_state_hash per tick."""
    sci_chain = build_hash_chain(seed, num_ticks, mode="autonomous")
    bench_chain = build_hash_chain(seed, num_ticks, mode="benchmark")
    first_failure: int | None = None
    sci_hash: str | None = None
    bench_hash: str | None = None
    for sci_entry, bench_entry in zip(sci_chain, bench_chain):
        if sci_entry.world_state_hash != bench_entry.world_state_hash:
            first_failure = sci_entry.tick
            sci_hash = sci_entry.world_state_hash
            bench_hash = bench_entry.world_state_hash
            break
    passed = first_failure is None
    deterministic_id = hashlib.sha256(f"{passed}:{num_ticks}:{first_failure}".encode()).hexdigest()
    return ParityReport(
        passed=passed,
        total_ticks=num_ticks,
        first_parity_failure_tick=first_failure,
        scientific_hash=sci_hash,
        benchmark_hash=bench_hash,
        deterministic_id=deterministic_id,
    )
