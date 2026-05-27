from fastapi import FastAPI, HTTPException
from dataclasses import asdict

from scrubin.control_plane.kernel import ControlPlaneKernel

# Initialize FastAPI app for the kernel API
app = FastAPI(title="ScrubIn Kernel API", version="0.1.0")

# The ControlPlaneKernel is deterministic; we can safely use a single instance.
# For the purposes of the API we don't need a real core interface, so we pass None.
kernel = ControlPlaneKernel(core_interface=None)

# ---------------------------------------------------------------------------
# Visualization utilities
# ---------------------------------------------------------------------------
from scrubin.visualization import VisualizationService

# Create a single shared service instance.
viz_service = VisualizationService(kernel)


@app.post("/run")
def run_simulation(config: dict):
    """Submit a new isolated simulation run.

    The request body should be a JSON object describing the run configuration.
    The kernel returns an ``ExecutionArtifact`` which we translate into a concise
    response containing the run identifier, a deterministic hash, and the number
    of ticks executed.
    """
    artifact = kernel.run_simulation(config)
    return {
        "run_id": artifact.run_id,
        "hash": artifact.metadata.get("hash"),
        "ticks": artifact.metadata.get("ticks"),
    }


@app.get("/run/{run_id}")
def get_run(run_id: str):
    """Retrieve the full ``ExecutionArtifact`` for a given run identifier."""
    artifact = kernel.get_run(run_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Run not found")
    # Convert dataclass to a dict for JSON serialization
    return asdict(artifact)


@app.get("/replay/{run_id}")
def replay(run_id: str):
    """Return the deterministic trajectory and final state for a run."""
    artifact = kernel.get_run(run_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "trajectory": artifact.trajectory,
        "final_state": artifact.final_state,
    }


@app.get("/trace/{run_id}")
def trace(run_id: str):
    """Placeholder trace endpoint.

    The current system does not store per‑run trace data in a format that can be
    exposed directly through the API. This endpoint is provided for forward
    compatibility and returns an empty list.
    """
    # In a full implementation this would pull trace information from the
    # ControlPlaneTracer or a dedicated tracing store.
    return {"trace": []}


@app.get("/view/{run_id}")
def view_run(run_id: str):
    """Return a visualization‑ready view of the run.

    The response bundles the raw run data, a simple phase‑space extraction and
    any adversarial anomalies detected in the trajectory.
    """
    try:
        return viz_service.get_view(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
