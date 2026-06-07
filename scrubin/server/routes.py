from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from ..api.session_manager import SessionManager
from ..api.persistent_session_store import PersistentSessionStore, SessionMetadata
from ..api.api_contracts import (
    SimulationCreateRequest,
    SimulationCreateResponse,
    SimulationActionRequest,
    SimulationActionResponse,
    SimulationStateResponse,
)

from . import dependency_provider as dp
from .error_models import (
    ValidationError,
    SessionNotFoundError,
    PersistenceError,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic request models – thin wrappers around the internal dataclasses.
# ---------------------------------------------------------------------------
class CreateRequestModel(BaseModel):
    seed: int = Field(..., description="Deterministic RNG seed for the session")
    initial_tick: int = Field(0, description="Starting simulation tick")

class ActionRequestModel(BaseModel):
    action_type: str = Field(..., description="High‑level deterministic action identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action‑specific parameters")
    timestamp: int = Field(0, description="Logical tick at which the action is issued")

# ---------------------------------------------------------------------------
# Endpoint implementations
# ---------------------------------------------------------------------------
@router.post("/session/create", response_model=SimulationCreateResponse)
def create_session(
    req: CreateRequestModel,
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
):
    # Convert to internal contract and delegate.
    internal_req = SimulationCreateRequest(seed=req.seed, initial_tick=req.initial_tick)
    resp = manager.create_session(internal_req)
    return jsonable_encoder(resp)

@router.get("/session/{session_id}/state", response_model=SimulationStateResponse)
def get_state(
    session_id: str,
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
):
    try:
        resp = manager.get_state(session_id)
    except KeyError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    return jsonable_encoder(resp)

@router.post("/session/{session_id}/action", response_model=SimulationActionResponse)
def post_action(
    session_id: str,
    req: ActionRequestModel,
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
):
    # Build internal request; session_id is derived from path.
    internal_req = SimulationActionRequest(
        session_id=session_id,
        action_type=req.action_type,
        parameters=req.parameters,
        timestamp=req.timestamp,
    )
    try:
        resp = manager.apply_action(internal_req)
    except KeyError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    return jsonable_encoder(resp)

@router.post("/session/{session_id}/save")
def save_session(
    session_id: str,
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    try:
        # Retrieve current world state via manager.
        world_state = manager.get_state(session_id).current_world_state
        try:
            metadata = store.save_session(session_id, world_state)
        except FileNotFoundError:
            metadata = store.create_session(session_id, world_state)
    except KeyError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    except Exception as exc:  # Catch any I/O‑related errors.
        raise PersistenceError(message=str(exc), code=500)
    return jsonable_encoder({"metadata": metadata})

@router.post("/session/{session_id}/load")
def load_session(
    session_id: str,
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    try:
        world, meta = store.load_session(session_id)
        # Update the in‑memory manager to reflect the loaded world.
        manager.set_state(session_id, world)
    except FileNotFoundError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    except Exception as exc:
        raise PersistenceError(message=str(exc), code=500)
    # Return the restored state using the same shape as /state.
    resp = manager.get_state(session_id)
    return jsonable_encoder({"metadata": meta, "state": resp})

@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
):
    try:
        store.delete_session(session_id)
        # Also drop from the in‑memory manager if present.
        try:
            manager.delete_session(session_id)
        except Exception:
            pass
    except FileNotFoundError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    except Exception as exc:
        raise PersistenceError(message=str(exc), code=500)
    return {"detail": f"Session {session_id} deleted"}

@router.get("/sessions", response_model=List[str])
def list_sessions(
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    try:
        ids = store.list_sessions()
    except Exception as exc:
        raise PersistenceError(message=str(exc), code=500)
    return ids

# ---------------------------------------------------------------------------
# Exception handlers – translate custom error models to HTTP responses.
# ---------------------------------------------------------------------------
