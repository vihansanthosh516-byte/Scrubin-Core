from typing import Dict, Any, List, Optional
from scrubin.control_plane.jobs import Job
from scrubin.control_plane.snapshots import Snapshot

class ControlPlaneInspector:
    """
    Debugging tools for inspecting control plane internal state.
    """
    def __init__(self, kernel: Any):
        self.kernel = kernel

    def inspect_job(self, job_id: str) -> Dict[str, Any]:
        job = self.kernel.jobs.get_job(job_id)
        if not job:
            return {"error": "Job not found"}
            
        # Enrich job data with traces and integrity checks
        return {
            "job_details": job,
            "integrity": self._get_job_integrity(job_id),
            "recovery_options": self.kernel.recovery.attempt_recovery(job_id)
        }

    def compare_snapshots(self, snap_id_a: str, snap_id_b: str) -> Dict[str, Any]:
        snap_a = self.kernel.snapshots.get_snapshot(snap_id_a)
        snap_b = self.kernel.snapshots.get_snapshot(snap_id_b)
        
        if not snap_a or not snap_b:
            return {"error": "One or both snapshots not found"}
            
        # Basic diff logic
        diffs = {}
        all_keys = set(snap_a.state_blob.keys()) | set(snap_b.state_blob.keys())
        for k in all_keys:
            val_a = snap_a.state_blob.get(k)
            val_b = snap_b.state_blob.get(k)
            if val_a != val_b:
                diffs[k] = {"a": val_a, "b": val_b}
                
        return {
            "snapshots": [snap_id_a, snap_id_b],
            "diff_count": len(diffs),
            "diffs": diffs,
            "identical": len(diffs) == 0
        }

    def _get_job_integrity(self, job_id: str) -> str:
        # Placeholder for integrity check
        return "VALIDATED"
