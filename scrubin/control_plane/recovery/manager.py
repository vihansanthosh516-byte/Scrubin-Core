from typing import Dict, Any, Optional, List
from scrubin.control_plane.jobs import Job, JobStatus
from scrubin.control_plane.snapshots import Snapshot

class RecoveryManager:
    """
    Handles job failure recovery, checkpointing, and partial replays.
    """
    def __init__(self, job_manager: Any, snapshot_manager: Any):
        self.jobs = job_manager
        self.snapshots = snapshot_manager
        self.recovery_journal: Dict[str, Dict[str, Any]] = {}

    def record_checkpoint(self, job_id: str, tick: int, snapshot_id: str):
        """
        Marks a known good state for a job.
        """
        self.recovery_journal[job_id] = {
            "last_tick": tick,
            "snapshot_id": snapshot_id,
            "status": "CHECKPOINTED"
        }

    def attempt_recovery(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyzes a failed job and proposes recovery parameters.
        """
        job = self.jobs.get_job(job_id)
        if not job or job.status != JobStatus.FAILED:
            return None
            
        journal = self.recovery_journal.get(job_id)
        if not journal:
            print(f"[RECOVERY] No recovery journal for job {job_id}. Full restart required.")
            return {"strategy": "FULL_RESTART"}
            
        return {
            "strategy": "RESUME_FROM_CHECKPOINT",
            "resume_tick": journal["last_tick"],
            "snapshot_id": journal["snapshot_id"]
        }

    def reconcile_state(self, job_id: str, target_state: Dict[str, Any]):
        """
        Verifies that a reconstructed job state matches the original checkpoint.
        """
        # In a real system, this would compare hashes of snapshots
        pass
