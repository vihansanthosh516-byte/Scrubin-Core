from typing import Optional

from scrubin.replay.snapshots import SnapshotEngine, WorldSnapshot
from scrubin.replay.hash import world_hash
from scrubin.contracts.validator import InvariantValidator
from scrubin.world.model import SimulationWorld
from scrubin.world.hospital import HospitalWorld


class RecoveryEngine:
    def __init__(self, snapshot_engine: SnapshotEngine, invariant_validator: InvariantValidator | None = None):
        self._snapshot_engine = snapshot_engine
        self._invariant_validator = invariant_validator

    def recover_to_tick(
        self,
        target_tick: int,
        evolve_fn=None,
    ) -> Optional[SimulationWorld | HospitalWorld]:
        snapshot = self._snapshot_engine.latest_before(target_tick)
        if snapshot is None:
            return None
        world = self._snapshot_engine.restore(snapshot)
        if evolve_fn is not None:
            while world.tick < target_tick:
                evolve_fn(world)
        if self._invariant_validator is not None:
            self._invariant_validator.validate(world)
        final_hash = world_hash(world)
        return world

    def verify_recovery(
        self,
        world: SimulationWorld | HospitalWorld,
        expected_hash: str,
    ) -> dict:
        actual_hash = world_hash(world)
        violations = []
        if self._invariant_validator is not None:
            violations = self._invariant_validator.validate_soft(world)
        return {
            "hash_matched": actual_hash == expected_hash,
            "actual_hash": actual_hash,
            "expected_hash": expected_hash,
            "invariant_violations": len(violations),
        }
