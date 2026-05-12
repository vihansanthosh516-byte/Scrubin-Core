from enum import Enum, auto
from typing import List, Dict, Any, Optional
import queue
from scrubin.control_plane.jobs import Job, JobType, JobStatus

class ExecutionBackend(Enum):
    LOCAL = auto()
    DISTRIBUTED = auto()
    GPU_ACCELERATED = auto()

class ResourceScheduler:
    """
    Schedules jobs and allocates resources (Vectorized Batching).
    """
    def __init__(self, backend: ExecutionBackend = ExecutionBackend.LOCAL):
        self.backend = backend
        self.pending_queue = queue.Queue()
        self.running_jobs: Dict[str, Job] = {}

    def submit(self, job: Job):
        job.status = JobStatus.QUEUED
        self.pending_queue.put(job)

    def allocate_vectorized_batch(self, jobs: List[Job]) -> List[Job]:
        """
        Group individual simulation jobs into a vectorized batch for efficiency.
        Control Plane only manages the batching, doesn't execute the math.
        """
        # Logic to group jobs based on config compatibility
        return jobs

    def process_next(self) -> Optional[Job]:
        if not self.pending_queue.empty():
            job = self.pending_queue.get()
            job.status = JobStatus.RUNNING
            self.running_jobs[job.id] = job
            return job
        return None
