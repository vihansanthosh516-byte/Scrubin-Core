'''StreamManager – WebSocket connection & deterministic tick streaming.

Implements a lightweight manager that stores active WebSocket connections per
`run_id` and streams incremental simulation updates (tick, state, anomalies,
control signals). It runs the deterministic `DummyKernel` step‑by‑step in an
asyncio task, preserving the order of ticks for replay consistency.
'''

import asyncio
import copy
import uuid
from typing import Any, Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

# Minimal deterministic kernel used for P8 unit tests – deterministic and fast.
from scrubin.control_plane.p8.dummy_kernel import DummyKernel
# Load procedure definitions for phase‑aware streaming.
from scrubin.procedures.registry import get_procedure

def compute_phase(tick: int, total_ticks: int, phases: list[str]) -> tuple[int | None, str | None]:
    """Utility to compute deterministic phase information.

    Returns ``(phase_index, phase_name)``. If ``phases`` is empty the result is ``(None, None)``.
    """
    if not phases:
        return None, None
    phase_len = max(1, total_ticks // len(phases))
    idx = min(len(phases) - 1, tick // phase_len)
    return idx, phases[idx]

# Helper to compute a centroid (same logic used by the frontend visualization).
def _compute_centroid(state: Dict[str, Any]) -> float:
    numeric = [v for v in state.values() if isinstance(v, (int, float))]
    return sum(numeric) / len(numeric) if numeric else 0.0


from scrubin.learning.adaptive_engine import get_adaptive_feedback

class StreamManager:
    """Manage WebSocket connections and broadcast deterministic tick updates.

    * Connections are stored per ``run_id`` – a set of ``WebSocket`` objects.
    * ``start_simulation`` spawns an async task that iterates the kernel tick by
      tick, broadcasting a minimal payload after each tick.
    * Disconnect handling removes stale sockets and cleans up empty run buckets.
    """

    def __init__(self) -> None:
        # Mapping run_id -> set of open websockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Protect concurrent modifications of the dict
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------------------
    # Connection lifecycle
    # ---------------------------------------------------------------------
    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        """Accept a new websocket and register it for the given ``run_id``."""
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(run_id, set()).add(websocket)

    async def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        """Remove a websocket from the registry; clean empty buckets."""
        async with self._lock:
            conns = self._connections.get(run_id)
            if conns and websocket in conns:
                conns.remove(websocket)
                if not conns:
                    # No more listeners – drop the entry
                    self._connections.pop(run_id, None)

    async def _broadcast(self, run_id: str, message: Dict[str, Any]) -> None:
        """Send ``message`` to every websocket listening on ``run_id``.

        Faulty connections are removed automatically.
        """
        # Snapshot the current connections to avoid holding the lock while sending.
        async with self._lock:
            targets = list(self._connections.get(run_id, set()))
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                # Assume the client disconnected; clean up.
                await self.disconnect(run_id, ws)

    # ---------------------------------------------------------------------
    # Simulation execution & streaming
    # ---------------------------------------------------------------------
    async def start_simulation(self, config: Dict[str, Any]) -> str:
        """Create a new ``run_id`` and begin streaming deterministic ticks.

        Returns the ``run_id`` immediately – the caller can open a websocket to
        ``/stream/{run_id}`` to receive updates.
        """
        run_id = str(uuid.uuid4())
        # Fire‑and‑forget the simulation task. ``asyncio.create_task`` ensures the
        # coroutine runs in the background without blocking the request handler.
        asyncio.create_task(self._run_and_stream(run_id, config))
        return run_id

    async def _run_and_stream(self, run_id: str, config: Dict[str, Any]) -> None:
        """Execute the deterministic kernel tick‑by‑tick, broadcasting each step.

        Payload format now includes procedure‑aware phase information:
        {
            "type": "tick",
            "run_id": ...,
            "tick": ...,
            "procedure_id": <str|None>,
            "phase": <str|None>,
            "phase_index": <int|None>,
            "state": ...,
            "anomalies": [...],
            "centroid": ...
        }
        A final ``type: "complete"`` message also carries the last phase info.
        """
        seed = config.get("seed", 42)
        ticks = config.get("ticks", 100)
        initial_state = copy.deepcopy(config.get("initial_state", {}))

        # Load procedure phases if a procedure_id is supplied (deterministic).
        proc_id = config.get("procedure_id")
        phases: list[str] = []
        if proc_id:
            try:
                proc = get_procedure(proc_id)
                phases = proc.get("phases", [])
            except FileNotFoundError:
                phases = []

        # Initialise deterministic kernel – identical to the one used in IsolationEngine.
        kernel = DummyKernel(seed=seed)
        state = initial_state

        for tick in range(ticks):
            # Deterministic transition
            state = kernel.step(state)
            # Detect simple anomalies – any key named ``adversary_event``.
            anomalies: list[Dict[str, Any]] = []
            if isinstance(state, dict) and "adversary_event" in state:
                anomalies.append({"tick": tick, "event": state["adversary_event"]})

            phase_index, phase_obj = compute_phase(tick, ticks, phases)
            # Resolve phase fields, handling legacy string phases gracefully.
            if isinstance(phase_obj, dict):
                phase_name = phase_obj.get("name")
                objective = phase_obj.get("objective")
                instructions = phase_obj.get("instructions")
                success_criteria = phase_obj.get("success_criteria")
                risk_flags = phase_obj.get("risk_flags")
            else:
                phase_name = phase_obj
                objective = None
                instructions = None
                success_criteria = None
                risk_flags = None
            payload = {
                "type": "tick",
                "run_id": run_id,
                "tick": tick,
                "procedure_id": proc_id,
                "phase": phase_name,
                "phase_index": phase_index,
                "objective": objective,
                "instructions": instructions,
                "success_criteria": success_criteria,
                "risk_flags": risk_flags,
                "state": state,
                "anomalies": anomalies,
                "centroid": _compute_centroid(state),
            }
            await self._broadcast(run_id, payload)
            # Small pause to yield control to the event loop – adjust as needed.
            await asyncio.sleep(0.01)

        # Final completion payload – include last phase info for consistency.
        final_phase_index, final_phase_name = compute_phase(ticks - 1, ticks, phases) if ticks > 0 else (None, None)
        complete_payload = {
            "type": "complete",
            "run_id": run_id,
            "ticks": ticks,
            "procedure_id": proc_id,
            "phase": final_phase_name,
            "phase_index": final_phase_index,
            "final_state": state,
        }
        # Compute adaptive feedback for this run (used by frontend focus panel)
        adaptive_feedback = get_adaptive_feedback(user_id="default", run_info=complete_payload)
        complete_payload["adaptive_feedback"] = adaptive_feedback
        await self._broadcast(run_id, complete_payload)


# Export a singleton for FastAPI to reuse.
stream_manager = StreamManager()
