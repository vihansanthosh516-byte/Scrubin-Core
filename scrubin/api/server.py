import asyncio
import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scrubin.api.sessions import SessionManager
from scrubin.services.simulation_service import SimulationService
from scrubin.api.mappers import map_patient_profile_to_dto
from scrubin.patient.profile import PATIENT_PROFILES
from scrubin.tester.profiles.registry import PROFILES


app = FastAPI(title="ScrubIn API", version="0.3.0")
manager = SessionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    seed: int = 42
    profile: str = "default"
    patient_profile: str = "standard"
    mode: str = "autonomous"


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


@app.post("/session/start", response_model=StartResponse)
def start_session(req: StartRequest):
    if req.mode not in ("autonomous", "interactive"):
        raise HTTPException(status_code=400, detail="mode must be 'autonomous' or 'interactive'")
    session = manager.create(
        seed=req.seed,
        profile_name=req.profile,
        patient_profile_id=req.patient_profile,
        mode=req.mode,
    )
    return StartResponse(
        session_id=session.session_id,
        patient_profile=session.patient_profile.id,
        mode=session.mode,
    )


@app.post("/session/tick", response_model=TickResponse)
def tick_session(req: TickRequest):
    session = _session_or_404(req.session_id)
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
def get_options(session_id: str = Query(...)):
    session = _session_or_404(session_id)
    return OptionsResponse(
        tick=session.current_tick(),
        options=session.get_options(),
    )


@app.get("/session/state", response_model=StateResponse)
def get_state(session_id: str = Query(...)):
    session = _session_or_404(session_id)
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
def get_summary(session_id: str = Query(...)):
    session = _session_or_404(session_id)
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
def get_ledger(session_id: str = Query(...), limit: int = Query(default=20, ge=1, le=500)):
    session = _session_or_404(session_id)
    return LedgerResponse(events=session.get_recent_events(limit))


@app.get("/session/events", response_model=EventsSinceResponse)
def get_events_since(session_id: str = Query(...), after: int = Query(default=-1, ge=-1)):
    session = _session_or_404(session_id)
    return EventsSinceResponse(events=session.get_events_since(after))


@app.post("/session/decide", response_model=DecisionResponse)
def apply_decision(req: DecisionRequest):
    session = _session_or_404(req.session_id)
    result = session.apply_decision(req.option_id, req.target)
    return DecisionResponse(
        executed=result.get("executed", False),
        action=result.get("action", ""),
        target=result.get("target", ""),
        reason=result.get("reason", ""),
        intent_id=result.get("intent_id", ""),
    )


@app.post("/session/reset", response_model=ResetResponse)
def reset_session(req: TickRequest):
    session = _session_or_404(req.session_id)
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
    await websocket.accept()
    session = manager.get(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": f"session {session_id} not found"})
        await websocket.close()
        return

    last_sequence = -1
    await websocket.send_json({
        "type": "state_snapshot",
        "summary": session.get_summary(),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid json"})
                continue

            command = msg.get("command", "")
            data = msg.get("data", {})

            if command == "tick":
                steps = data.get("steps", 1)
                session.tick_session(steps)
                new_events = session.get_events_since(last_sequence)
                for evt in new_events:
                    await websocket.send_json({"type": "event", "event": evt})
                    last_sequence = evt["sequence"]
                await websocket.send_json({
                    "type": "state_snapshot",
                    "summary": session.get_summary(),
                })

            elif command == "decide":
                option_id = data.get("option_id", "")
                target = data.get("target", "")
                result = session.apply_decision(option_id, target)
                new_events = session.get_events_since(last_sequence)
                for evt in new_events:
                    await websocket.send_json({"type": "event", "event": evt})
                    last_sequence = evt["sequence"]
                await websocket.send_json({
                    "type": "decision_result",
                    "result": result,
                    "summary": session.get_summary(),
                })

            elif command == "ping":
                await websocket.send_json({"type": "pong"})

            elif command == "subscribe":
                pass

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"unknown command: {command}",
                })

    except WebSocketDisconnect:
        pass
