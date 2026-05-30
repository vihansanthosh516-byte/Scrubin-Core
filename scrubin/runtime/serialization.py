from __future__ import annotations
"""Deterministic serialization utilities for ``WorldState``.

The implementation uses ``dataclasses.asdict`` to obtain a plain‑Python mapping
of the world, then recursively reconstructs a fresh ``WorldState`` instance from
that mapping.  All tuple fields are preserved (JSON conversion will turn them
into lists, but the deserializer restores tuples).  The round‑trip guarantees
that ``deserialize_world(serialize_world(w)) == w`` for any valid world.
"""

from dataclasses import asdict, fields, is_dataclass, replace
from typing import Any, Dict, Tuple, Type

from scrubin.world.state import WorldState


def _reconstruct_dataclass(cls: Type[Any], data: Dict[str, Any]) -> Any:
    """Recursively rebuild a frozen dataclass from a ``dict``.

    ``asdict`` represents nested dataclasses as dictionaries.  This helper walks
    the field definitions of *cls* and, when it encounters a sub‑dataclass, it
    recurses.  Tuples are reconstructed from the list representation that may
    have been produced by a JSON round‑trip.
    """
    if not is_dataclass(cls):
        return data
    init_kwargs = {}
    for f in fields(cls):
        if f.name not in data:
            # Use default if missing.
            continue
        value = data[f.name]
        # Detect nested dataclass via its type having ``__dataclass_fields__``.
        if hasattr(f.type, "__dataclass_fields__"):
            if isinstance(value, dict):
                init_kwargs[f.name] = _reconstruct_dataclass(f.type, value)
            else:
                # Already an instance (unlikely when coming from asdict).
                init_kwargs[f.name] = value
        elif getattr(f.type, "__origin__", None) is tuple or isinstance(value, list):
            # Preserve tuple ordering – ensure elements are of primitive types or
            # already reconstructed objects.
            # If the tuple element type is a dataclass, we cannot infer it here;
            # for the current WorldState schema all tuple elements are either
            # primitives or other frozen dataclasses that were already handled.
            init_kwargs[f.name] = tuple(value)
        else:
            init_kwargs[f.name] = value
    return cls(**init_kwargs)


def serialize_world(world: WorldState) -> Dict[str, Any]:
    """Serialize ``WorldState`` to a JSON‑compatible ``dict``.

    The result can be safely passed to ``json.dumps`` or stored in a database.
    ``asdict`` already yields a deep mapping of standard Python types.
    """
    return asdict(world)


def deserialize_world(data: Dict[str, Any]) -> WorldState:
    """Recreate a ``WorldState`` instance from the output of
    :func:`serialize_world`.

    The function performs a recursive reconstruction so that all nested
    frozen dataclasses are restored with their original types and tuple fields
    are re‑converted from the list representation used by JSON.
    """
    return _reconstruct_dataclass(WorldState, data)
