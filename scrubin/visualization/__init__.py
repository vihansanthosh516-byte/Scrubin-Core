"""Visualization utilities and services for ScrubIn.

Provides functions to transform a raw ``ExecutionArtifact`` into a structure
suitable for UI consumption, as well as the ``VisualizationService`` wrapper
that ties these helpers to the kernel.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def format_run_for_view(artifact: Any) -> Dict[str, Any]:
    """Convert an ``ExecutionArtifact`` into a UI‑friendly dictionary.

    The ``artifact`` may be a dataclass, a plain ``dict`` or a simple object
    with attributes. We first attempt to turn it into a dictionary via
    ``asdict`` (which works for dataclasses). If that fails we fall back to
    attribute access.
    """
    # Try dataclass conversion – may raise if ``artifact`` is not a dataclass.
    try:
        artifact_dict: dict | None = asdict(artifact)  # type: ignore[assignment]
    except Exception:
        artifact_dict = None

    if artifact_dict is not None:
        # ``artifact`` was a dataclass – all data lives in the dict.
        return {
            "run_id": artifact_dict.get("run_id"),
            "timeline": artifact_dict.get("trajectory"),
            "final_state": artifact_dict.get("final_state"),
            "hash": artifact_dict.get("metadata", {}).get("hash"),
            "ticks": len(artifact_dict.get("trajectory", [])),
        }
    else:
        # Fallback to attribute access. ``metadata`` itself is expected to be a dict.
        meta = getattr(artifact, "metadata", {})
        return {
            "run_id": getattr(artifact, "run_id", None),
            "timeline": getattr(artifact, "trajectory", None),
            "final_state": getattr(artifact, "final_state", None),
            "hash": meta.get("hash") if isinstance(meta, dict) else None,
            "ticks": len(getattr(artifact, "trajectory", [])),
        }



def extract_phase_points(trajectory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map a trajectory to a list of *phase space* points.

    For each tick we compute the centroid of all numeric values in the state.
    The result is a list of ``{"t": int, "centroid": float}`` dictionaries.
    Non‑numeric fields are ignored.
    """
    points: List[Dict[str, Any]] = []
    for t, state in enumerate(trajectory):
        numeric_values = [v for v in state.values() if isinstance(v, (int, float))]
        if numeric_values:
            centroid = sum(numeric_values) / len(numeric_values)
            points.append({"t": t, "centroid": centroid})
    return points


def extract_anomalies(trajectory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract adversarial events from a trajectory.

    Any state that contains an ``adversary_event`` key is considered an anomaly.
    The returned list contains ``{"tick": int, "event": Any}`` entries.
    """
    anomalies: List[Dict[str, Any]] = []
    for t, state in enumerate(trajectory):
        if "adversary_event" in state:
            anomalies.append({"tick": t, "event": state["adversary_event"]})
    return anomalies


# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------

class VisualizationService:
    """High‑level service providing a UI‑ready representation of a run.

    The service is thin – it simply fetches the ``ExecutionArtifact`` from the
    kernel and runs the helper transforms defined above.
    """

    def __init__(self, kernel: Any) -> None:
        self.kernel = kernel

    def get_view(self, run_id: str) -> Dict[str, Any]:
        """Return a composite view consisting of the run data, phase‑space
        points and any detected anomalies.
        """
        artifact = self.kernel.get_run(run_id)
        if not artifact:
            raise ValueError(f"Run {run_id} not found")
        return {
            "run": format_run_for_view(artifact),
            "phase_space": extract_phase_points(artifact.trajectory),
            "anomalies": extract_anomalies(artifact.trajectory),
        }

__all__ = [
    "format_run_for_view",
    "extract_phase_points",
    "extract_anomalies",
    "VisualizationService",
]
