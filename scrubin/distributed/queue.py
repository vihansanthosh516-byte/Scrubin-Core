"""In‑memory async job queue for the distributed layer.

A thin wrapper around ``asyncio.Queue`` that stores :class:`ExecutionJob`
objects.  For a production system this would be a persistent queue (e.g. Redis),
but for the single‑machine prototype a simple in‑memory queue suffices.
"""
import asyncio
from typing import List

from .job import ExecutionJob

# Global queue instance – shared by the scheduler and any producers.
_job_queue: asyncio.Queue[ExecutionJob] = asyncio.Queue()

async def enqueue(job: ExecutionJob) -> None:
    """Place a job onto the queue."""
    await _job_queue.put(job)

def get_queue() -> asyncio.Queue[ExecutionJob]:
    """Return the underlying ``asyncio.Queue`` – useful for the scheduler."""
    return _job_queue

def list_queued() -> List[ExecutionJob]:
    """Return a *snapshot* of the queued jobs.

    NOTE: ``asyncio.Queue`` does not expose its items publicly.  For this
    prototype we reach into the protected ``_queue`` attribute which holds a
    ``collections.deque`` of pending items.  This is acceptable for a test
    environment but would be replaced by a proper persistence layer later.
    """
    return list(_job_queue._queue)  # type: ignore[attr-defined]
