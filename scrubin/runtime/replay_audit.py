from __future__ import annotations
"""Replay audit utilities.

The audit aggregates deterministic metadata for a given ``WorldState`` – useful
for validating that a replay reproduces the original simulation.  The output
structure mirrors the legacy ``scrubin.replay`` audit objects but is simplified
for unit‑testing purposes.
"""

from hashlib import sha256
import json
from typing import Dict, Any

from scrubin.world.state import WorldState


def _hash_object(obj: Any) -> str:
    """Return a deterministic SHA‑256 hash for a generic object.

    The object is first serialised using ``json.dumps`` with sorted keys and a
    stable numeric representation (the same rules as ``scrubin.replay``).  This
    helper is used for both timeline and semantic‑graph checks.
    """
    # Convert dataclasses to dicts via ``asdict`` for a stable representation.
    from dataclasses import asdict

    if hasattr(obj, "__dataclass_fields__"):
        data = asdict(obj)
    else:
        data = obj
    json_repr = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return sha256(json_repr.encode()).hexdigest()


def generate_replay_audit(world: WorldState) -> Dict[str, Any]:
    """Generate a deterministic audit record for *world*.

    The audit includes:
    * ``seed`` – the simulation seed.
    * ``tick`` – current tick.
    * ``timeline_hash`` – SHA‑256 of the timeline events list.
    * ``semantic_hash`` – SHA‑256 of the active semantic graph.
    * ``competency`` – current overall competency value.
    * ``recovery_trajectory`` – placeholder (None) – can be extended.
    * ``consequence_summary`` – simple count of active complications.
    """
    audit: Dict[str, Any] = {
        "seed": getattr(world, "seed", None),
        "tick": getattr(world, "tick", None),
        "timeline_hash": _hash_object(world.timeline),
        "semantic_hash": _hash_object(world.active_semantic_graph),
        "competency": getattr(world, "operator_competency_profile", None).overall_competency
        if hasattr(world, "operator_competency_profile")
        else None,
        "recovery_trajectory": None,
        "consequence_summary": len(getattr(world, "complications", None).active) if hasattr(world, "complications") else 0,
    }
    return audit
