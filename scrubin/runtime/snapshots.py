from __future__ import annotations
"""Simple snapshot utilities for ``WorldState``.

A snapshot is a deep copy of a ``WorldState`` instance together with the tick at
which it was captured.  The API mirrors the existing replay snapshot engine but
is lightweight and deterministic for unit testing.
"""

import copy
from dataclasses import asdict
from typing import Any, Dict

from scrubin.world.state import WorldState


def create_snapshot(world: WorldState) -> Dict[str, Any]:
    """Create a deterministic snapshot of *world*.

    The snapshot is represented as a dictionary containing the tick and a deep
    copy of the world data (as a plain mapping).  Using a plain ``dict`` makes the
    snapshot JSON‑serialisable without further conversion.
    """
    return {
        "tick": world.tick,
        "data": copy.deepcopy(asdict(world)),
    }


def restore_snapshot(snapshot: Dict[str, Any]) -> WorldState:
    """Restore a ``WorldState`` from a snapshot produced by ``create_snapshot``.
    """
    from scrubin.runtime.serialization import deserialize_world

    data = snapshot["data"]
    world = deserialize_world(data)
    # Ensure the tick matches the stored tick (the deserialized world already
    # contains its own tick value, but we enforce consistency).
    return world.with_tick(snapshot["tick"])


def diff_snapshots(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a deterministic diff between two snapshots.

    Returns a mapping of field names to a tuple ``(value_in_a, value_in_b)`` for
    fields that differ.  Only top‑level fields are compared; deeper inspection is
    delegated to higher‑level utilities if required.
    """
    diff: Dict[str, Any] = {}
    data_a = a["data"]
    data_b = b["data"]
    for key in set(data_a) | set(data_b):
        val_a = data_a.get(key)
        val_b = data_b.get(key)
        if val_a != val_b:
            diff[key] = (val_a, val_b)
    return diff
