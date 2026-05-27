from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class ExecutionArtifact:
    """Stores all artifacts from an isolated run.

    Attributes
    ----------
    run_id: str
        Unique identifier for the run.
    final_state: Dict[str, Any]
        State after the last tick.
    trajectory: List[Dict[str, Any]]
        Sequence of state snapshots captured each tick.
    metadata: Dict[str, Any]
        Miscellaneous metadata (seed, ticks, hash, etc.).
    """
    run_id: str
    final_state: Dict[str, Any]
    trajectory: List[Dict[str, Any]]
    metadata: Dict[str, Any]
