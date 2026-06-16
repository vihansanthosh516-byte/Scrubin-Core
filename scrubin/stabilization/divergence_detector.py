"""Divergence detector – compares two hash chains and reports first differing tick."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Tuple, List

from scrubin.stabilization.hash_chain_validator import HashChainEntry

@dataclass(frozen=True)
class DivergenceReport:
    diverged: bool
    first_divergence_tick: int | None
    divergent_fields: Tuple[str, ...]
    identical_ticks: int
    total_ticks: int
    deterministic_id: str

def detect_divergence(chain_a: Tuple[HashChainEntry, ...], chain_b: Tuple[HashChainEntry, ...]) -> DivergenceReport:
    """Compare two hash chains field‑by‑field and return a report.

    If the chains differ in length, divergence is reported at the first missing tick.
    """
    len_a = len(chain_a)
    len_b = len(chain_b)
    total = max(len_a, len_b)
    identical = 0
    first_tick: int | None = None
    fields: List[str] = []
    for i in range(total):
        if i >= len_a or i >= len_b:
            # One chain ended before the other
            first_tick = i + 1  # ticks are 1‑based
            fields = ["chain_length"]
            break
        a = chain_a[i]
        b = chain_b[i]
        if (
            a.world_state_hash == b.world_state_hash
            and a.physiology_hash == b.physiology_hash
            and a.cognition_hash == b.cognition_hash
            and a.resource_hash == b.resource_hash
            and a.agent_hash == b.agent_hash
            and a.rl_snapshot_hash == b.rl_snapshot_hash
        ):
            identical += 1
            continue
        # Found divergence
        first_tick = a.tick
        # Determine which fields differ
        if a.world_state_hash != b.world_state_hash:
            fields.append("world_state_hash")
        if a.physiology_hash != b.physiology_hash:
            fields.append("physiology_hash")
        if a.cognition_hash != b.cognition_hash:
            fields.append("cognition_hash")
        if a.resource_hash != b.resource_hash:
            fields.append("resource_hash")
        if a.agent_hash != b.agent_hash:
            fields.append("agent_hash")
        if a.rl_snapshot_hash != b.rl_snapshot_hash:
            fields.append("rl_snapshot_hash")
        break
    diverged = first_tick is not None
    deterministic_id = hashlib.sha256(f"{diverged}:{first_tick}:{identical}".encode()).hexdigest()
    return DivergenceReport(
        diverged=diverged,
        first_divergence_tick=first_tick,
        divergent_fields=tuple(fields),
        identical_ticks=identical,
        total_ticks=total,
        deterministic_id=deterministic_id,
    )
