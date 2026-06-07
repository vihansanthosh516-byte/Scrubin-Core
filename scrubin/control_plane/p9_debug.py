# Debug integration – bridge for deterministic replay and analysis (Phase P.9).
"""
Provides a ``DebugFacade`` that wires the P.9 debug utilities onto the control‑plane
kernel. It enables inspection of isolated runs (P.8) without mutating any state.
"""

from __future__ import annotations

from typing import Callable, List, Any

# Import the debug utilities.
from scrubin.debug.replay_inspector import ReplayInspector
from scrubin.debug.causal_trace_engine import CausalTraceEngine
from scrubin.debug.run_diff_engine import diff_runs, RunDiff
from scrubin.debug.timeline_query_engine import query_timeline as _query_timeline


class DebugFacade:
    """Facade exposing deterministic debug operations on the control‑plane kernel.

    The class is deliberately read‑only: all methods operate on stored ``ExecutionArtifact``
    objects and never modify the underlying world state.
    """

    def __init__(self, kernel: Any):
        self.kernel = kernel
        # The isolation engine used for P.8 runs.
        self.engine = getattr(kernel, "p8_engine", None)
        if self.engine is None:
            raise AttributeError("Kernel does not expose a p8_engine attribute required for debugging")

    # ---------------------------------------------------------------------
    # Helper to fetch an ExecutionArtifact.
    # ---------------------------------------------------------------------
    def _get_artifact(self, run_id: str) -> Any:
        artifact = self.kernel.get_run(run_id)
        if artifact is None:
            raise ValueError(f"Run {run_id} not found")
        return artifact

    # ---------------------------------------------------------------------
    # Replay inspection.
    # ---------------------------------------------------------------------
    def replay_inspect(self, run_id: str, ticks: int | None = None) -> List[Any]:
        """Replay a run tick‑by‑tick.

        Parameters
        ----------
        run_id: str
            Identifier of the stored run.
        ticks: int | None, optional
            Number of ticks to replay. If omitted, the full length of the stored
            trajectory is used.
        Returns
        -------
        List[ReplayFrame]
            Deterministic frames describing each tick.
        """
        artifact = self._get_artifact(run_id)
        total_ticks = len(getattr(artifact, "trajectory", []))
        if ticks is None:
            ticks = total_ticks
        # Instantiate the underlying deterministic kernel (e.g., DummyKernel) using the run's seed.
        kernel_cls = getattr(self.engine, "kernel_cls", None)
        if kernel_cls is None:
            raise AttributeError("IsolationEngine does not expose a kernel_cls attribute")
        seed = getattr(self._get_artifact(run_id), "metadata", {}).get("seed", 0)
        kernel_instance = kernel_cls(seed=seed)
        inspector = ReplayInspector(kernel_instance)
        # Use an empty dict as the initial state – this matches the IsolationEngine's default.
        return inspector.replay(initial_state={}, ticks=ticks)

    # ---------------------------------------------------------------------
    # Causal trace.
    # ---------------------------------------------------------------------
    def causal_trace(self, run_id: str, target_tick: int, target_description: str) -> Any:
        """Construct a causal trace for a specific event in a run.
        """
        artifact = self._get_artifact(run_id)
        engine = CausalTraceEngine()
        return engine.trace(artifact, target_tick, target_description)

    # ---------------------------------------------------------------------
    # Run diff.
    # ---------------------------------------------------------------------
    def run_diff(self, run_id_a: str, run_id_b: str) -> RunDiff:
        """Compare two runs and return a ``RunDiff`` summary.
        """
        a = self._get_artifact(run_id_a)
        b = self._get_artifact(run_id_b)
        return diff_runs(a, b)

    # ---------------------------------------------------------------------
    # Timeline query.
    # ---------------------------------------------------------------------
    def query_timeline(self, run_id: str, predicate: Callable[[Any], bool]) -> List[Any]:
        """Filter timeline events from the final state of a run.
        """
        artifact = self._get_artifact(run_id)
        # Prefer the final_state if available; otherwise use the last trajectory entry.
        final_state = getattr(artifact, "final_state", None) or (artifact.trajectory[-1] if getattr(artifact, "trajectory", None) else None)
        if final_state is None:
            raise ValueError("Run does not contain a final state to query")
        return _query_timeline(final_state, predicate)
