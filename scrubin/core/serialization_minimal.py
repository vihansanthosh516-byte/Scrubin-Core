"""Minimal world‑state serialization for benchmark mode.

Provides a lightweight deterministic hash of the world state without the
heavy cognition‑related fields. The function mirrors the full ``world_hash``
but omits any fields that are not part of the scientific‐mode hash.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def minimal_world_hash(world: Any) -> str:
    """Compute a deterministic hash of the world state for benchmark mode.

    The hash includes only the core deterministic components that are required
    for replay certification in scientific mode.  It deliberately excludes any
    cognition‑derived or logging fields.
    """
    # Extract a minimal dict representation – reuse the ``to_dict`` method but
    # strip out fields that are not part of the core physics.
    core_dict = {
        "tick": world.tick,
        "physiology": world.physiology.to_dict(),
        "organ_state": world.organ_state.to_dict(),
        "hidden_state": {k: v for k, v in sorted(world.hidden_state.items())},
        "observed_vitals": {k: round(v, 6) for k, v in sorted(world.observed_vitals.items())},
        "mortality_risk": round(world.mortality_risk, 6),
    }
    canonical = json.dumps(core_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
