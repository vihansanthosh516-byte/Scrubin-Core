import json
from typing import Any

from scrubin.world.model import SimulationWorld
from scrubin.world.hospital import HospitalWorld


def _stable_serialize(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int,)):
        return obj
    if isinstance(obj, float):
        r = round(obj, 6)
        if r == -0.0:
            r = 0.0
        return r
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {k: _stable_serialize(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [_stable_serialize(item) for item in obj]
    if hasattr(obj, "to_dict"):
        return _stable_serialize(obj.to_dict())
    return repr(obj)


def canonical_json(world: SimulationWorld | HospitalWorld) -> str:
    data = _stable_serialize(world)
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
