from typing import Dict, Any, List
from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.jobs import JobType

class ControlPlaneAPI:
    """
    Public API for the ScrubIn Control Plane.
    Exposes Phase 12 capabilities via jobs.
    """
    def __init__(self, kernel: ControlPlaneKernel):
        self.kernel = kernel

    def launch_hierarchical_simulation(self, config: Dict[str, Any]):
        exp = ExperimentConfig(
            name="Hierarchical Run",
            phase12_mode=True,
            policy_overrides=config.get("overrides", {})
        )
        return self.kernel.run_workload(exp)

    def launch_vector_batch(self, size: int):
        exp = ExperimentConfig(
            name="Vector Batch",
            vectorized=True,
            cohort_size=size
        )
        return self.kernel.run_workload(exp)

    def launch_tournament(self, agents: List[str]):
        # Custom job for tournament
        job = self.kernel.jobs.create_job(JobType.TOURNAMENT_RUN, {"agents": agents})
        self.kernel.scheduler.submit(job)
        return job.id

    def get_job_status(self, job_id: str):
        job = self.kernel.jobs.get_job(job_id)
        return job.status.name if job else "NOT_FOUND"

    def get_session_snapshots(self, session_id: str):
        return self.kernel.snapshots.list_for_session(session_id)
