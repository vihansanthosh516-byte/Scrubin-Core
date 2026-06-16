"""Deterministic JSON (de)serialization utilities for ``WorldState``.

Only a minimal, deterministic round‑trip is required for the API layer.
The implementation uses ``dataclasses.asdict`` to convert the immutable
``WorldState`` (and its nested frozen dataclasses) into plain Python types.
All collections are converted to JSON‑compatible structures; tuples become
lists, which are deterministic because the original ordering is preserved.
When deserialising we reconstruct a ``WorldState`` using the class
constructor – this works because the default values of all sub‑states are
identical to those produced by the Scrubin core.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from scrubin.world.state import WorldState


def _convert_to_serializable(obj: Any) -> Any:
    """Recursively turn dataclasses/tuples into JSON‑serialisable structures.

    * ``dataclass`` → ``asdict`` (recurses automatically).
    * ``tuple`` → ``list`` (preserves order).
    * ``list``/``dict`` → handled by ``json``.
    """
    if isinstance(obj, tuple):
        return [_convert_to_serializable(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        # Serialize only fields that are part of the init signature (init=True).
        field_dict = {}
        for f_name, f_def in obj.__dataclass_fields__.items():
            if f_def.init:
                value = getattr(obj, f_name)
                field_dict[f_name] = _convert_to_serializable(value)
        return field_dict
    if isinstance(obj, list):
        return [_convert_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _convert_to_serializable(v) for k, v in obj.items()}
    return obj


def serialize_worldstate(world: WorldState) -> str:
    """Deterministically serialize a ``WorldState`` to a JSON string.

    The output uses ``sort_keys=True`` to guarantee stable key ordering.
    """
    serialisable = _convert_to_serializable(world)
    return json.dumps(serialisable, sort_keys=True, separators=(",", ":"))


def deserialize_worldstate(payload: str) -> WorldState:
    """Deserialize a JSON string back into an immutable ``WorldState``.

    The JSON must have been produced by :func:`serialize_worldstate`. This
    implementation resolves forward‑referenced type hints and recursively
    reconstructs nested frozen dataclasses, converting JSON lists back to tuples
    where appropriate.
    """
    data = json.loads(payload)
    from dataclasses import is_dataclass, fields
    from typing import get_type_hints, get_origin, get_args, Any

    def _reconstruct_dataclass(cls, datum):
        """Recursively rebuild a frozen dataclass from a dict.

        Handles forward‑referenced annotations via ``get_type_hints`` and
        restores tuple fields from JSON lists.
        """
        if not is_dataclass(cls):
            return datum
        # Resolve type hints (including forward references)
        type_hints = get_type_hints(cls)
        init_kwargs = {}
        for f in fields(cls):
            if f.name not in datum:
                continue
            value = datum[f.name]
            hint = type_hints.get(f.name, f.type)
            origin = get_origin(hint)
            # Tuple handling – convert list to tuple, reconstruct elements
            if origin is tuple:
                args = get_args(hint)
                elem_type = args[0] if args and args[0] is not Ellipsis else Any
                if isinstance(value, list):
                    init_kwargs[f.name] = tuple(_reconstruct_dataclass(elem_type, v) if isinstance(v, dict) else v for v in value)
                else:
                    init_kwargs[f.name] = tuple()
                continue
            # Dataclass handling
            if hasattr(hint, "__dataclass_fields__") and isinstance(value, dict):
                init_kwargs[f.name] = _reconstruct_dataclass(hint, value)
            else:
                init_kwargs[f.name] = value
        return cls(**init_kwargs)

    return _reconstruct_dataclass(WorldState, data)
