from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional


@dataclass
class DiagnosticTask:
    id: str
    type: str  # 'lab', 'imaging', 'consult'
    description: str
    request_tick: int
    completion_tick: int
    result: Any = None
    status: str = "pending"  # "pending", "completed", "cancelled"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "request_tick": self.request_tick,
            "completion_tick": self.completion_tick,
            "status": self.status,
            "result": self.result,
        }


class DiagnosticQueue:
    def __init__(self):
        self.pending_tasks: List[DiagnosticTask] = []
        self.completed_tasks: List[DiagnosticTask] = []
        self._task_counter = 0

    def request(self, task_type: str, description: str, current_tick: int, delay: int, result: Any = None) -> str:
        self._task_counter += 1
        task_id = f"dx-{self._task_counter:04d}"
        task = DiagnosticTask(
            id=task_id,
            type=task_type,
            description=description,
            request_tick=current_tick,
            completion_tick=current_tick + delay,
            result=result,
            status="pending"
        )
        self.pending_tasks.append(task)
        return task_id

    def update(self, current_tick: int) -> List[DiagnosticTask]:
        """
        Move tasks from pending to completed if their completion tick has passed.
        Returns a list of newly completed tasks.
        """
        newly_completed = []
        remaining_pending = []
        
        for task in self.pending_tasks:
            if task.completion_tick <= current_tick:
                task.status = "completed"
                self.completed_tasks.append(task)
                newly_completed.append(task)
            else:
                remaining_pending.append(task)
        
        self.pending_tasks = remaining_pending
        return newly_completed

    def get_task(self, task_id: str) -> Optional[DiagnosticTask]:
        for task in self.pending_tasks + self.completed_tasks:
            if task.id == task_id:
                return task
        return None

    def to_dict(self) -> dict:
        return {
            "pending": [t.to_dict() for t in self.pending_tasks],
            "completed": [t.to_dict() for t in self.completed_tasks],
        }
