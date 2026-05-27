from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ExecutionContext:
    """Encapsulates all information needed to run an isolated simulation.

    Attributes
    ----------
    run_id: str
        Unique identifier for the run.
    seed: int
        Random seed for deterministic execution.
    config: dict
        Configuration governing the run (e.g., number of ticks).
    initial_state: dict, optional
        Optional initial state to seed the kernel; not used by default kernels.
    """
    run_id: str
    seed: int
    config: Dict[str, Any]
    initial_state: Dict[str, Any] = None
