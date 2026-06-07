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
    AuthorizationError,
)
from ..auth.user import UserIdentity
from ..auth.dependencies import get_current_user

router = APIRouter()

def _ensure_owner(user: UserIdentity, session_id: str, manager: SessionManager, store: PersistentSessionStore) -> None:
    # Check in manager's in-memory ownership mapping first.
    owners = getattr(manager, "_owners", {})
    if session_id in owners:
        if owners[session_id] != user.user_id:
            raise AuthorizationError(message="Forbidden: session not owned by user", code=403)
        return
    # Fallback to persisted metadata.
    try:
        meta = store.get_metadata(session_id)
    except FileNotFoundError:
        raise SessionNotFoundError(message=f"Session {session_id} not found", code=404)
    if meta.owner_user_id != user.user_id:
        raise AuthorizationError(message="Forbidden: session not owned by user", code=403)

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
    user: UserIdentity = Depends(get_current_user),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
):
    # Convert to internal contract and delegate.
    internal_req = SimulationCreateRequest(seed=req.seed, initial_tick=req.initial_tick)
    resp = manager.create_session(internal_req, user.user_id)
    return jsonable_encoder(resp)

@router.get("/session/{session_id}/state", response_model=SimulationStateResponse)
def get_state(
    session_id: str,
    user: UserIdentity = Depends(get_current_user),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    _ensure_owner(user, session_id, manager, store)
    try:
        resp = manager.get_state(session_id)
    except KeyError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    return jsonable_encoder(resp)

@router.post("/session/{session_id}/action", response_model=SimulationActionResponse)
def post_action(
    session_id: str,
    req: ActionRequestModel,
    user: UserIdentity = Depends(get_current_user),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    # Build internal request; session_id is derived from path.
    internal_req = SimulationActionRequest(
        session_id=session_id,
        action_type=req.action_type,
        parameters=req.parameters,
        timestamp=req.timestamp,
    )
    _ensure_owner(user, session_id, manager, store)
    try:
        resp = manager.apply_action(internal_req)
    except KeyError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    return jsonable_encoder(resp)

@router.post("/session/{session_id}/save")
def save_session(
    session_id: str,
    user: UserIdentity = Depends(get_current_user),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    _ensure_owner(user, session_id, manager, store)
    try:
        world_state = manager.get_state(session_id).current_world_state
        metadata = store.save_session(session_id, world_state, user.user_id)
    except FileNotFoundError:
        metadata = store.create_session(session_id, world_state, user.user_id)
    except KeyError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    except Exception as exc:
        raise PersistenceError(message=str(exc), code=500)
    return jsonable_encoder({"metadata": metadata})

@router.post("/session/{session_id}/load")
def load_session(
    session_id: str,
    user: UserIdentity = Depends(get_current_user),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    _ensure_owner(user, session_id, manager, store)
    try:
        world, meta = store.load_session(session_id)
        manager.set_state(session_id, world, owner_user_id=user.user_id)
    except FileNotFoundError as exc:
        raise SessionNotFoundError(message=str(exc), code=404)
    except Exception as exc:
        raise PersistenceError(message=str(exc), code=500)
    resp = manager.get_state(session_id)
    return jsonable_encoder({"metadata": meta, "state": resp})

@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    user: UserIdentity = Depends(get_current_user),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
):
    _ensure_owner(user, session_id, manager, store)
    try:
        store.delete_session(session_id)
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
    user: UserIdentity = Depends(get_current_user),
    manager: SessionManager = Depends(lambda: dp.get_session_manager()),
    store: PersistentSessionStore = Depends(lambda: dp.get_persistent_store()),
):
    # Combine in‑memory sessions owned by the user with persisted sessions.
    in_memory_ids = [sid for sid, owner in getattr(manager, "_owners", {}).items() if owner == user.user_id]
    persisted_ids = []
    try:
        persisted_ids = store.list_sessions_for_user(user.user_id)
    except Exception as exc:
        raise PersistenceError(message=str(exc), code=500)
    # Deduplicate while preserving order via set.
    ids = sorted(set(in_memory_ids + persisted_ids))
    return ids

# ---------------------------------------------------------------------------
# Misc endpoints – health & readiness
# ---------------------------------------------------------------------------

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/ready")
def ready():
    return {"status": "ready"}

# ---------------------------------------------------------------------------
# Exception handlers – translate custom error models to HTTP responses.
# ---------------------------------------------------------------------------
