from __future__ import annotations
"""Deterministic hashing utilities for WorldState.

Provides a stable SHA‑256 hash of a ``WorldState`` instance using the same
canonical serialization logic employed by the replay subsystem.
"""

import json
from hashlib import sha256
from dataclasses import asdict

# Re‑use the stable serialization helper from the existing replay package.
from scrubin.replay.canonical import _stable_serialize
from scrubin.world.state import WorldState


def deterministic_world_hash(world: WorldState) -> str:
    """Return a SHA‑256 hash string for *world*.

    The world is first converted to a stable, sorted JSON representation via
    ``_stable_serialize`` (the same routine used by ``scrubin.replay``).  The
    resulting JSON string is encoded as UTF‑8 and hashed with SHA‑256.  The hash
    is deterministic because the serialization orders dictionary keys and
    rounds floating‑point numbers to six decimal places, matching the existing
    replay guarantees.
    """
    # ``asdict`` recursively converts dataclasses into plain Python types.
    # ``_stable_serialize`` then normalises ordering, number rounding and
    # tuple handling.
    data = _stable_serialize(asdict(world))
    json_repr = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return sha256(json_repr.encode()).hexdigest()


def compare_world_hashes(a: WorldState, b: WorldState) -> bool:
    """Return ``True`` if *a* and *b* produce the same deterministic hash.

    This is a convenience wrapper used by tests that require a quick equality
    check without performing a full dataclass comparison (which would also be
    deterministic but may be more expensive for large worlds).
    """
    return deterministic_world_hash(a) == deterministic_world_hash(b)
