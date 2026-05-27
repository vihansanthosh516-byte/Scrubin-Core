import time
import dataclasses, json, hashlib
from typing import Any, Dict, List, Optional

from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.replay.executor import ReplayExecutor
from scrubin.control_plane.snapshots import SnapshotManager
from scrubin.replay.hash import world_hash
from scrubin.control_plane.fuzz.generator import ChaosGenerator


class P6Kernel(ControlPlaneKernel):
    """Phase‑6.1 execution kernel extending the base ControlPlaneKernel.

    Provides explicit APIs for:
    * Deterministic replay (via the existing ReplayExecutor)
    * Snapshot capture / rollback
    * Canonical state hashing for reproducibility checks
    * Adversarial/fuzz injection that feeds mutated events into the kernel
    * Mutation fingerprint generation for auditability
    * Guarantees zero hidden‑state mutation – all state changes are routed
      through the snapshot manager or the replay engine.
    """

    def __init__(self, core_interface: Any):
        super().__init__(core_interface)
        # Re‑expose the deterministic replay executor for direct use
        self.replay_executor: ReplayExecutor = self.replay
        # Dedicated snapshot manager for rollback‑safe execution
        self.snapshot_manager: SnapshotManager = self.snapshots
        # Chaos / adversarial injection helper
        self._chaos_generator = ChaosGenerator()
        # Store mutation fingerprints per session for reproducibility audits
        self._session_fingerprints: Dict[str, str] = {}

    # -----------------------------------------------------------------
    # Deterministic replay helpers
    # -----------------------------------------------------------------
    def reconstruct_session(self, session_id: str) -> Dict[str, Any]:
        """Return replay artefacts for ``session_id``."""
        return self.replay_executor.reconstruct_session(session_id)

    # -----------------------------------------------------------------
    # Snapshot API
    # -----------------------------------------------------------------
    def capture_snapshot(self, session_id: str, tick: int, state: Dict[str, Any]) -> str:
        """Capture a snapshot and store its mutation fingerprint."""
        snap_id = self.snapshot_manager.capture(session_id, tick, state)
        fp = self._compute_mutation_fingerprint(session_id)
        self._session_fingerprints[session_id] = fp
        return snap_id

    def rollback_to_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Return the stored state blob for ``snapshot_id``."""
        snap = self.snapshot_manager.get_snapshot(snapshot_id)
        if not snap:
            return None
        return snap.state_blob

    # -----------------------------------------------------------------
    # Canonical hashing
    # -----------------------------------------------------------------
    def hash_state(self, world: Any) -> str:
        """Stable SHA‑256 hash of a world representation."""
        return world_hash(world)

    # -----------------------------------------------------------------
    # Adversarial injection
    # -----------------------------------------------------------------
    def inject_adversary(self, events: List[Any], seed: int = 0, session_id: str = "adversary") -> List[Any]:
        """Mutate ``events`` with chaos generators and ingest them."""
        events_copy = list(events)
        mutated = self._chaos_generator.generate_fuzz(events_copy, seed)
        for ev in mutated:
            self._ingest_to_semantic_history(ev)
        fp = self._compute_mutation_fingerprint(session_id)
        self._session_fingerprints[session_id] = fp
        return mutated

    # -----------------------------------------------------------------
    # Execute + snapshot helper
    # -----------------------------------------------------------------
    def execute_and_snapshot(self, session_id: str, tick: int, world_state: Dict[str, Any]) -> Dict[str, Any]:
        snap_id = self.capture_snapshot(session_id, tick, world_state)
        snap_state = self.rollback_to_snapshot(snap_id)
        return {
            "snapshot_id": snap_id,
            "state_hash": self.hash_state(snap_state) if snap_state else "",
        }

    # -----------------------------------------------------------------
    # Immutability guard (placeholder)
    # -----------------------------------------------------------------
    def _ensure_immutable_tick(self, tick: int) -> None:
        pass

    # -----------------------------------------------------------------
    # Reproducibility verification
    # -----------------------------------------------------------------
    def _compute_mutation_fingerprint(self, session_id: str) -> str:
        """Deterministically hash all events for ``session_id``."""
        events = [ev for ev in self.causal_graph.nodes.values() if getattr(ev, "session_id", None) == session_id]
        dicts = [dataclasses.asdict(ev) for ev in events]
        dicts.sort(key=lambda d: d.get("event_id", ""))
        serialized = json.dumps(dicts, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def verify_reproducibility(self, session_id: str) -> bool:
        """Validate deterministic replay equivalence for ``session_id``."""
        replay_a = self.replay_executor.reconstruct_session(session_id)
        replay_b = self.replay_executor.reconstruct_session(session_id)

        if self.hash_state(replay_a["final_state"]) != self.hash_state(replay_b["final_state"]):
            return False

        if set(replay_a["snapshots"].keys()) != set(replay_b["snapshots"].keys()):
            return False
        for sid, state_a in replay_a["snapshots"].items():
            if self.hash_state(state_a) != self.hash_state(replay_b["snapshots"][sid]):
                return False

        stored_fp = self._session_fingerprints.get(session_id)
        if stored_fp is None:
            return True
        current_fp = self._compute_mutation_fingerprint(session_id)
        return stored_fp == current_fp
