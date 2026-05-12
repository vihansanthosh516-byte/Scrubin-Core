from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid
import time

class JobType(Enum):
    HIERARCHICAL_SIMULATION = auto()
    MULTI_AGENT_SIMULATION = auto()
    VECTOR_BATCH_SIMULATION = auto()
    ONLINE_LEARNING = auto()
    COUNTERFACTUAL_BATCH = auto()
    TOURNAMENT_RUN = auto()

class JobStatus(Enum):
    PENDING = auto()
    QUEUED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class Job:
    id: str = field(default_factory=lambda: f"job-{uuid.uuid4().hex[:8]}")
    type: JobType = JobType.HIERARCHICAL_SIMULATION
    config: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class JobManager:
    """
    Manages the lifecycle of clinical simulation jobs.
    """
    def __init__(self):
        self.jobs: Dict[str, Job] = {}

    def create_job(self, job_type: JobType, config: Dict[str, Any]) -> Job:
        job = Job(type=job_type, config=config)
        self.jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = status
            if status == JobStatus.RUNNING:
                job.started_at = time.time()
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job.completed_at = time.time()
                job.result = result
                job.error = error
