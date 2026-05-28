"""Registry of active workers for the distributed execution prototype.

The registry holds a mapping of ``worker_id`` → :class:`Worker` instances and
provides convenience methods for the API layer.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .worker import Worker


class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: Dict[str, Worker] = {}

    # -----------------------------------------------------------------
    # Worker management
    # -----------------------------------------------------------------
    def register(self, worker: Worker) -> None:
        self._workers[worker.worker_id] = worker

    def list_workers(self) -> List[Dict]:
        """Return a lightweight description of each worker for the API."""
        return [
            {
                "worker_id": w.worker_id,
                "status": w.current_status,
                "current_job_id": w.current_job.job_id if w.current_job else None,
                "jobs_completed": w.jobs_completed,
            }
            for w in self._workers.values()
        ]

    def get_idle_worker(self) -> Optional[Worker]:
        for w in self._workers.values():
            if w.is_idle:
                return w
        return None

    # -----------------------------------------------------------------
    # Job aggregation (used by the /jobs API)
    # -----------------------------------------------------------------
    def all_jobs(self) -> List[Dict]:
        jobs: List[Dict] = []
        for w in self._workers.values():
            if w.current_job:
                jobs.append(w.current_job.asdict())
            jobs.extend(w.history)
        return jobs

    def get_job(self, job_id: str) -> Optional[Dict]:
        for w in self._workers.values():
            if w.current_job and w.current_job.job_id == job_id:
                return w.current_job.asdict()
            for hist in w.history:
                if hist["job_id"] == job_id:
                    return hist
        return None


# Singleton used throughout the FastAPI app
worker_registry = WorkerRegistry()
