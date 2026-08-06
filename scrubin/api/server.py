import asyncio
import json
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
from typing import List
from scrubin.procedures.registry import list_procedures as list_procedures_from_registry
from scrubin.procedures.registry import get_procedure
from pydantic import BaseModel

class ProcedureInfo(BaseModel):
    id: str
    name: str

class VariantInfo(BaseModel):
    id: str
    display_name: str
    description: str
    difficulty: float

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scrubin.api.sessions import SessionManager
from scrubin.services.simulation_service import SimulationService
from scrubin.api.mappers import map_patient_profile_to_dto
from scrubin.patient.profile import PATIENT_PROFILES
from scrubin.tester.profiles.registry import PROFILES
from scrubin.auth.dependencies import get_current_user
from scrubin.auth.user import UserIdentity


app = FastAPI(title="ScrubIn API", version="0.3.0")


manager = SessionManager()

# CORS origins: read an explicit allowlist from the environment. The default keeps
# local development ergonomic WITHOUT enabling credentialed cross-origin requests
# from anywhere. ``allow_credentials=True`` is incompatible with ``allow_origins=["*"]``
# and is an invalid/dangerous configuration; therefore a wildcard origin is never used.
_DEFAULT_ORIGINS = "http://localhost:3000,http://localhost:5173,http://localhost:8000"
_allowed = [o.strip() for o in os.getenv("SCRUBIN_ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    seed: int = 42
    profile: str = "default"
    patient_profile: str = "standard"
    mode: str = "autonomous"
    procedure_id: str | None = None
    variant_id: str | None = None


class StartResponse(BaseModel):
    session_id: str
    patient_profile: str
    mode: str


class TickRequest(BaseModel):
    session_id: str
    steps: int = 1


class TickResponse(BaseModel):
    tick: int
    vitals: Optional[dict]
    last_events: list[dict]
    last_decision: Optional[dict]
    mode: str
    options: list[dict]


class OptionsResponse(BaseModel):
    tick: int
    options: list[dict]


class StateResponse(BaseModel):
    tick: int
    vitals: Optional[dict]
    active_complication: Optional[dict]
    last_procedure: Optional[dict]
    patient_profile: str
    mode: str
    options: list[dict]


class SummaryResponse(BaseModel):
    tick: int
    vitals: Optional[dict]
    active_complication: Optional[dict]
    last_procedure: Optional[dict]
    last_decision: Optional[dict]
    last_validation: Optional[dict]
    last_execution: Optional[dict]
    patient_profile: str
    mode: str
    options: list[dict]


class LedgerResponse(BaseModel):
    events: list[dict]


class ResetResponse(BaseModel):
    session_id: str
    message: str


class DecisionRequest(BaseModel):
    session_id: str
    option_id: str
    target: str = ""


class DecisionResponse(BaseModel):
    executed: bool
    action: str
    target: str
    reason: str = ""
    intent_id: str = ""


class ProfilesResponse(BaseModel):
    patient_profiles: list[dict]
    stress_profiles: list[str]


class EventsSinceResponse(BaseModel):
    events: list[dict]


def _session_or_404(session_id: str) -> SimulationService:
    session = manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    return session


def _owned_session(session_id: str, user: UserIdentity) -> SimulationService:
    """Return the session only if it exists AND is owned by ``user``.

    Owner resolution: the in‑memory ``_owners`` map is authoritative; if a session
    predates owner tracking it falls back to ``default_user`` ownership (matching
    the dev‑mode auth fallback) so existing sessions remain accessible.
    """
    session = _session_or_404(session_id)
    owner = manager.owner_of(session_id)
    if owner is None:
        owner = "default_user"
    if owner != user.user_id:
        raise HTTPException(status_code=403, detail=f"session {session_id} not owned by user")
    return session


@app.post("/session/start", response_model=StartResponse)
def start_session(req: StartRequest, user: UserIdentity = Depends(get_current_user)):
    # Existing implementation unchanged
    
    # (the body of the function follows as before)
    # Existing implementation unchanged
    
    if req.mode not in ("autonomous", "interactive"):
        raise HTTPException(status_code=400, detail="mode must be 'autonomous' or 'interactive'")
    session = manager.create(
        seed=req.seed,
        profile_name=req.profile,
        patient_profile_id=req.patient_profile,
        mode=req.mode,
        procedure_id=req.procedure_id,
        variant_id=req.variant_id,
        owner_user_id=user.user_id,
    )
    return StartResponse(
        session_id=session.session_id,
        patient_profile=session.patient_profile.id,
        mode=session.mode,
    )

# ------------------------------------------------------------
# Procedure catalog endpoint (data‑driven UI)

@app.get("/procedures", response_model=List[ProcedureInfo])
def get_procedures():
    proc_defs = list_procedures_from_registry()
    out = []
    for pid, proc in proc_defs.items():
        name = proc.get("name") or proc.get("display_name") or proc.get("id") or pid
        out.append({"id": pid, "name": name})
    return out

@app.get("/procedure_variants", response_model=List[VariantInfo])
def get_procedure_variants(procedure_id: str = Query(...)):
    proc = get_procedure(procedure_id)
    variants = proc.get("patient_variants", [])
    sorted_variants = sorted(variants, key=lambda v: v.get("id", ""))
    out = []
    for v in sorted_variants:
        out.append({
            "id": v.get("id", ""),
            "display_name": v.get("display_name", ""),
            "description": v.get("description", ""),
            "difficulty": v.get("difficulty", 0),
        })
    return out


@app.post("/session/tick", response_model=TickResponse)
def tick_session(req: TickRequest, user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(req.session_id, user)
    session.tick_session(req.steps)
    snap = session.get_summary()
    return TickResponse(
        tick=snap["tick"],
        vitals=snap["vitals"],
        last_events=session.get_recent_events(5),
        last_decision=snap["last_decision"],
        mode=session.mode,
        options=session.get_options(),
    )


@app.get("/session/options", response_model=OptionsResponse)
def get_options(session_id: str = Query(...), user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(session_id, user)
    return OptionsResponse(
        tick=session.current_tick(),
        options=session.get_options(),
    )


@app.get("/session/state", response_model=StateResponse)
def get_state(session_id: str = Query(...), user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(session_id, user)
    snap = session.get_snapshot()
    return StateResponse(
        tick=snap["tick"],
        vitals=snap["vitals"],
        active_complication=snap["active_complication"],
        last_procedure=snap["last_procedure"],
        patient_profile=session.patient_profile.id,
        mode=session.mode,
        options=session.get_options(),
    )


@app.get("/session/summary", response_model=SummaryResponse)
def get_summary(session_id: str = Query(...), user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(session_id, user)
    snap = session.get_summary()
    return SummaryResponse(
        tick=snap["tick"],
        vitals=snap["vitals"],
        active_complication=snap["active_complication"],
        last_procedure=snap["last_procedure"],
        last_decision=snap["last_decision"],
        last_validation=snap["last_validation"],
        last_execution=snap["last_execution"],
        patient_profile=snap["patient_profile"],
        mode=snap["mode"],
        options=snap["options"],
    )


@app.get("/session/ledger", response_model=LedgerResponse)
def get_ledger(session_id: str = Query(...), limit: int = Query(default=20, ge=1, le=500),
               user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(session_id, user)
    return LedgerResponse(events=session.get_recent_events(limit))


@app.get("/session/events", response_model=EventsSinceResponse)
def get_events_since(session_id: str = Query(...), after: int = Query(default=-1, ge=-1),
                     user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(session_id, user)
    return EventsSinceResponse(events=session.get_events_since(after))


@app.post("/session/decide", response_model=DecisionResponse)
def apply_decision(req: DecisionRequest, user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(req.session_id, user)
    result = session.apply_decision(req.option_id, req.target)
    return DecisionResponse(
        executed=result.get("executed", False),
        action=result.get("action", ""),
        target=result.get("target", ""),
        reason=result.get("reason", ""),
        intent_id=result.get("intent_id", ""),
    )


@app.post("/session/reset", response_model=ResetResponse)
def reset_session(req: TickRequest, user: UserIdentity = Depends(get_current_user)):
    session = _owned_session(req.session_id, user)
    new = manager.reset(req.session_id)
    if not new:
        raise HTTPException(status_code=404, detail=f"session {req.session_id} not found")
    return ResetResponse(
        session_id=new.session_id,
        message=f"session reset with seed={new.seed} profile={new.profile_name} patient={new.patient_profile.id} mode={new.mode}",
    )


@app.get("/profiles", response_model=ProfilesResponse)
def get_profiles():
    patient_profiles = [
        map_patient_profile_to_dto(p).to_dict()
        for p in PATIENT_PROFILES.values()
    ]
    stress_profiles = list(PROFILES.keys())
    return ProfilesResponse(
        patient_profiles=patient_profiles,
        stress_profiles=stress_profiles,
    )


@app.websocket("/session/{session_id}/ws")
async def session_websocket(websocket: WebSocket, session_id: str):
    # Resolve the caller identity BEFORE accepting the handshake so that auth
    # failures never open a stream. The same dependency used by HTTP routes is
    # applied manually here (WebSocket endpoint supports ``Depends`` too, but we
    # call it explicitly to control the close handshake precisely).
    try:
        user = get_current_user(websocket)
    except HTTPException:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "unauthorized"})
        await websocket.close(code=4401)
        return

    session = manager.get(session_id)
    if not session:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": f"session {session_id} not found"})
        await websocket.close()
        return

    # Ownership check (mirror of ``_owned_session`` for the WS path).
    owner = manager.owner_of(session_id)
    if owner is None:
        owner = "default_user"
    if owner != user.user_id:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "session not owned by user"})
        await websocket.close(code=4403)
        return

    await websocket.accept()
    # Send current state snapshot on connect
    session.event_queue.put_nowait({"type": "state_snapshot", "summary": session.get_summary()})

    try:
        while True:
            # Wait for next event from the session
            event = await session.event_queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        # No registry cleanup required
        pass
