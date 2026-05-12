import copy
from dataclasses import dataclass, field
from typing import List, Optional

from scrubin.replay.hash import world_hash
from scrubin.world.model import SimulationWorld
from scrubin.world.hospital import HospitalWorld


@dataclass
class WorldSnapshot:
    tick: int
    sequence_id: int
    world_hash: str
    compressed_state: bytes

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "sequence_id": self.sequence_id,
            "world_hash": self.world_hash,
            "compressed_size": len(self.compressed_state),
        }


class SnapshotEngine:
    def __init__(self, interval: int = 50, ledger=None, invariant_validator=None):
        self._interval = interval
        self._snapshots: List[WorldSnapshot] = []
        self._sequence = 0
        self._ledger = ledger
        self._invariant_validator = invariant_validator

    @property
    def interval(self) -> int:
        return self._interval

    @property
    def snapshots(self) -> List[WorldSnapshot]:
        return list(self._snapshots)

    def should_snapshot(self, tick: int) -> bool:
        if tick == 0:
            return False
        return tick % self._interval == 0

    def capture(self, world: SimulationWorld | HospitalWorld, tick: int) -> WorldSnapshot:
        from scrubin.replay.storage import SnapshotStorage
        snapshot_hash = world_hash(world)
        compressed = SnapshotStorage.compress(world)
        self._sequence += 1
        snapshot = WorldSnapshot(
            tick=tick,
            sequence_id=self._sequence,
            world_hash=snapshot_hash,
            compressed_state=compressed,
        )
        self._snapshots.append(snapshot)
        if self._ledger is not None:
            self._ledger.log(
                "world_snapshot",
                {"tick": tick, "hash": snapshot_hash, "sequence_id": self._sequence},
                tick=tick,
            )
        return snapshot

    def latest_before(self, tick: int) -> Optional[WorldSnapshot]:
        candidates = [s for s in self._snapshots if s.tick <= tick]
        return candidates[-1] if candidates else None

    def restore(self, snapshot: WorldSnapshot) -> SimulationWorld | HospitalWorld:
        from scrubin.replay.storage import SnapshotStorage
        from scrubin.replay.hash import world_hash
        world = SnapshotStorage.decompress(snapshot.compressed_state)
        loaded_hash = world_hash(world)
        if loaded_hash != snapshot.world_hash:
            raise ValueError(
                f"Snapshot integrity check failed: loaded={loaded_hash} != stored={snapshot.world_hash}"
            )
        if self._invariant_validator is not None:
            self._invariant_validator.validate(world)
        return world

    def recover_to(self, target_tick: int, evolve_fn=None) -> Optional[SimulationWorld | HospitalWorld]:
        snapshot = self.latest_before(target_tick)
        if snapshot is None:
            return None
        world = self.restore(snapshot)
        if evolve_fn is None:
            return world
        while world.tick < target_tick:
            evolve_fn(world)
        return world
