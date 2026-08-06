import json
import zlib
from typing import Any

from scrubin.world.model import SimulationWorld
from scrubin.world.hospital import HospitalWorld


def _world_to_jsonable(world: Any) -> dict:
    """Best-effort JSON-serializable representation of a world.

    Uses ``to_dict`` when available and coerces non-primitive/nested values to
    JSON-safe forms. Falls back to ``__dict__`` only when ``to_dict`` is absent.
    """
    if hasattr(world, "to_dict"):
        payload = world.to_dict()
    else:
        payload = getattr(world, "__dict__", {})

    def _coerce(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): _coerce(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_coerce(v) for v in value]
        if hasattr(value, "to_dict"):
            return _coerce(value.to_dict())
        return str(value)

    return {str(k): _coerce(v) for k, v in payload.items()}


class SnapshotStorage:
    """Compresses/decompresses world snapshots using zlib + JSON.

    Snarls are stored as JSON rather than pickle so that decompressing an
    attacker-influenced blob cannot execute arbitrary code (CWE-502).
    Round-trip fidelity is verified by the caller via :func:`world_hash`.
    """

    @staticmethod
    def compress(world: SimulationWorld | HospitalWorld) -> bytes:
        payload = _world_to_jsonable(world)
        # Tag the concrete class so decompress can dispatch correctly.
        payload["__class__"] = type(world).__name__
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return zlib.compress(data)

    @staticmethod
    def decompress(data: bytes) -> SimulationWorld | HospitalWorld:
        serialized = zlib.decompress(data)
        payload = json.loads(serialized.decode("utf-8"))
        # Dispatch to the appropriate from_dict based on a class marker, if present.
        cls_name = payload.get("__class__") if isinstance(payload, dict) else None
        if cls_name == "HospitalWorld":
            return HospitalWorld.from_dict(payload)
        return SimulationWorld.from_dict(payload)
