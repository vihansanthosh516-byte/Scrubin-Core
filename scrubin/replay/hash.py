from dataclasses import dataclass
from hashlib import sha256

from scrubin.replay.canonical import canonical_json
from scrubin.world.model import SimulationWorld
from scrubin.world.hospital import HospitalWorld


def world_hash(world: SimulationWorld | HospitalWorld) -> str:
    canonical = canonical_json(world)
    return sha256(canonical.encode()).hexdigest()


@dataclass
class ReplayProof:
    original_hash: str
    replayed_hash: str
    matched: bool

    @classmethod
    def verify(cls, world: SimulationWorld | HospitalWorld, original_hash: str) -> "ReplayProof":
        replayed = world_hash(world)
        return cls(
            original_hash=original_hash,
            replayed_hash=replayed,
            matched=replayed == original_hash,
        )
