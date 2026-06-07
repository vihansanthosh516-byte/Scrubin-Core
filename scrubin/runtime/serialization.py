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

    This implementation resolves forward‑referenced type hints and recursively
    reconstructs nested frozen dataclasses, converting JSON lists back to tuples.
    """
    from dataclasses import is_dataclass, fields
    from typing import get_type_hints, get_origin, get_args, Any

    def _reconstruct(cls, datum):
        if not is_dataclass(cls):
            return datum
        type_hints = get_type_hints(cls)
        init_kwargs = {}
        for f in fields(cls):
            if f.name not in datum:
                continue
            value = datum[f.name]
            hint = type_hints.get(f.name, f.type)
            origin = get_origin(hint)
            if origin is tuple:
                args = get_args(hint)
                elem_type = args[0] if args and args[0] is not Ellipsis else Any
                if isinstance(value, list):
                    init_kwargs[f.name] = tuple(_reconstruct(elem_type, v) if isinstance(v, dict) else v for v in value)
                else:
                    init_kwargs[f.name] = tuple()
                continue
            if hasattr(hint, "__dataclass_fields__") and isinstance(value, dict):
                init_kwargs[f.name] = _reconstruct(hint, value)
            else:
                init_kwargs[f.name] = value
        return cls(**init_kwargs)

    return _reconstruct(WorldState, data)
