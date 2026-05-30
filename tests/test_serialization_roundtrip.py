"""Round‑trip serialization test for ``WorldState``.

The test verifies that ``serialize_world`` followed by ``deserialize_world``
produces an object equal to the original, guaranteeing lossless deterministic
persistence.
"""

from scrubin.world.state import WorldState
from scrubin.runtime.serialization import serialize_world, deserialize_world


def test_world_serialization_roundtrip():
    original = WorldState(tick=0, seed=42)
    data = serialize_world(original)
    restored = deserialize_world(data)
    assert original == restored
