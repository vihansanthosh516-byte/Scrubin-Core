import copy
import hashlib
from typing import Any

from .execution_context import ExecutionContext
from .execution_artifact import ExecutionArtifact


class IsolationEngine:
    """P8 core engine ensuring isolated, deterministic, replayable runs.

    Parameters
    ----------
    kernel_cls: type
        Class implementing a deterministic ``step(state)`` method.
    """

    def __init__(self, kernel_cls: Any):
        self.kernel_cls = kernel_cls
        # Store artifacts by run_id for later retrieval
        self.store: dict[str, ExecutionArtifact] = {}

    def run(self, context: ExecutionContext) -> ExecutionArtifact:
        """Execute a single isolated simulation run.

        Returns
        -------
        ExecutionArtifact
            Captured run artifacts.
        """
        # Instantiate kernel with provided seed – kernel must accept ``seed`` kwarg
        kernel = self.kernel_cls(seed=context.seed)

        # Initialise state – deep‑copy to avoid mutation of the original dict
        state = copy.deepcopy(context.initial_state or {})
        trajectory: list[dict[str, Any]] = []

        # Number of ticks is taken from ``config``; default to 100 if unspecified
        ticks = context.config.get("ticks", 100)
        for _ in range(ticks):
            # ``step`` should return the new state dict
            state = kernel.step(state)
            trajectory.append(copy.deepcopy(state))

        artifact = ExecutionArtifact(
            run_id=context.run_id,
            final_state=state,
            trajectory=trajectory,
            metadata={
                "seed": context.seed,
                "ticks": len(trajectory),
                "hash": self._hash(trajectory),
            },
        )

        self.store[context.run_id] = artifact
        return artifact

    def _hash(self, trajectory: list[dict[str, Any]]) -> str:
        """Compute a deterministic SHA‑256 hash of the trajectory.

        The hash is calculated on the string representation of the trajectory
        (list of dicts) to guarantee reproducibility across runs.
        """
        return hashlib.sha256(str(trajectory).encode()).hexdigest()
