"""ScrubIn FastAPI shim – Scrubin‑Core Python engine.

Exposes the exact JSON contract the ScrubIn React UI consumes so the
Node/Express server can proxy to it transparently. All simulation logic
lives here (port of the original TypeScript deterministic engine), keeping
the simulation contract bit‑compatible with the legacy TS implementation
where it matters (RNG, vitals, decisions, scoring).

Routes:
  POST /start                  { seed?, procedure? } -> start response
  POST /next                   { session_id }        -> next-tick payload
  POST /decide                 { session_id, decision_id, option_id } -> decide payload
  POST /reset                  { session_id }        -> { ok: true }
  GET  /procedures                                    -> { procedures: [...] }
  GET  /scenarios                                     -> { scenarios: [...] }
  GET  /scenarios/{id}                                -> enriched scenario
  GET  /procedures/search?q=&difficulty=&tag=         -> { procedures: [...] }
  POST /evaluate                                      -> { notes } (Groq attending notes passthrough stub)
  GET  /health                                        -> { core: "up", sessions: N }
"""

from __future__ import annotations

import os
import time
import math
import secrets
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scrubin_core_engine import (
    SessionManager,
    list_procedures,
    get_procedure,
    procedure_exists,
)


# ─────────────────────────────────────────────────────────────────────────────
# App + CORS
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="ScrubIn Core Engine", version="1.0.0")

_DEFAULT_ORIGINS = "http://localhost:3000,http://localhost:5173,http://localhost:5000,http://localhost:8000"
_allowed = [o.strip() for o in os.getenv("SCRUBIN_ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Session manager (in‑memory, mirrors the Node SessionManager semantics)
# ─────────────────────────────────────────────────────────────────────────────

manager = SessionManager()
_session_counter = 0
_counter_lock = threading.Lock()


def _next_session_id(seed: int) -> str:
    global _session_counter
    with _counter_lock:
        _session_counter += 1
        n = _session_counter
    # Python base36 of a non‑negative int; JS uses seed.toString(36)
    def to_base36(num: int) -> str:
        if num == 0:
            return "0"
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"
        out = []
        n_ = num
        while n_:
            out.append(digits[n_ % 36])
            n_ //= 36
        return "".join(reversed(out))
    return f"sim_{n}_{to_base36(seed)}"


def _default_seed() -> int:
    # Deterministic‑ish default mirroring TS nextInt(1, 999999) using system RNG.
    return int.from_bytes(secrets.token_bytes(4), "big") % 999999 + 1


# ─────────────────────────────────────────────────────────────────────────────
# Request/response models
# ─────────────────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    seed: Optional[int] = None
    procedure: Optional[str] = None


class NextRequest(BaseModel):
    session_id: str
    # Optional stock-step report: the client owns the stock steps, so it tells
    # the core which step was completed so the debrief evaluation sees the case.
    step_index: Optional[int] = None
    step_correct: Optional[bool] = None
    step_label: Optional[str] = None
    # Surgical-step kind (access/exposure/vessel/dissect…) — drives the
    # physiologic step modifiers (incision surge, traction bradycardia, bleed).
    step_kind: Optional[str] = None


class DecideRequest(BaseModel):
    session_id: str
    decision_id: str
    option_id: str


class ResetRequest(BaseModel):
    session_id: Optional[str] = None


class EvaluateRequest(BaseModel):
    procedureName: Optional[str] = None
    patient: Optional[Any] = None
    outcomeBadge: Optional[str] = None
    outcomeSummary: Optional[str] = None
    totalDecisions: Optional[int] = None
    history: list[Any] = field(default_factory=list)


class ComplicateRequest(BaseModel):
    session_id: str
    complication: str
    # The stock step the trainee failed, which triggered this complication.
    step_index: Optional[int] = None
    step_label: Optional[str] = None
    step_kind: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Simulation routes
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/start")
def start(req: StartRequest):
    procedure_id = req.procedure or "appendectomy"
    if not procedure_exists(procedure_id):
        raise HTTPException(status_code=400, detail=f"Unknown procedure: {procedure_id}")
    seed = req.seed if isinstance(req.seed, int) else _default_seed()
    session = manager.create(_next_session_id(seed), seed, procedure_id)
    state = session.state
    return {
        "session_id": session.id,
        "tick": state["tick"],
        "procedure_id": state["procedureId"],
        "procedure_name": state["procedureName"],
        "patient": state["patient"],
        "patient_profile": state.get("patientProfile"),
        "total_ticks": state["totalTicks"],
        "mode": state.get("mode", "stock"),
        "physiological_reserve": state.get("physiologicalReserve", 100.0),
        "complication_count": state.get("complicationCount", 0),
    }


@app.post("/next")
def next_tick(req: NextRequest):
    session = manager.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # Report the completed stock step before advancing the engine, so the
    # debrief evaluation records the whole case (the client owns stock steps).
    if req.step_index is not None:
        session.orchestrator.record_stock_step(
            req.step_index, bool(req.step_correct), req.step_label
        )
    try:
        result = session.next(step_label=req.step_label, step_kind=req.step_kind)
    except Exception as e:
        msg = str(e)
        if msg == "Cannot advance tick without decision":
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
    pending = _sanitize_decision(result["pendingDecision"]) if result["pendingDecision"] else None
    state = session.state
    return {
        "tick": result["tick"],
        "vitals": result["vitalsAfter"],
        "escalation_phase": result["escalationPhase"],
        "procedure_phase": result["procedurePhase"],
        "active_complication": result["activeComplication"],
        "pending_decision": pending,
        "events": result["events"],
        "score": result["score"],
        "completed": state["completed"],
        "mode": state["mode"],
        "physiological_reserve": state.get("physiologicalReserve", 100.0),
        "complication_count": state.get("complicationCount", 0),
        "complication_source": state.get("complicationSource"),
        "complication_cause": state.get("complicationCause"),
        "evaluation": state.get("evaluation"),
        "correct_steps": state.get("correctSteps", 0),
        "total_steps": state.get("totalSteps", 0),
    }


@app.post("/decide")
def decide(req: DecideRequest):
    session = manager.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        result = session.submit_decision(req.decision_id, req.option_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    dr = result["decisionResult"]
    if dr:
        decision_result = {
            "wasCorrect": dr["wasCorrect"],
            "feedback": dr["feedback"],
            "scoreDelta": dr["scoreDelta"],
            "complicationTriggered": dr["complicationTriggered"],
        }
    else:
        decision_result = {
            "wasCorrect": False,
            "feedback": "",
            "scoreDelta": 0,
            "complicationTriggered": None,
        }
    pending = _sanitize_decision(result["pendingDecision"]) if result["pendingDecision"] else None
    state = session.state
    return {
        "tick": result["tick"],
        "vitals": result["vitalsAfter"],
        "escalation_phase": result["escalationPhase"],
        "procedure_phase": result["procedurePhase"],
        "active_complication": result["activeComplication"],
        "pending_decision": pending,
        "decision_result": decision_result,
        "next_tick_ready": bool(result.get("pendingDecisionState", {}) and result["pendingDecisionState"].get("resolved")),
        "events": result["events"],
        "score": result["score"],
        "completed": state["completed"],
        "correct_decisions": state["correctDecisions"],
        "total_decisions": state["totalDecisions"],
        "mode": state["mode"],
        "physiological_reserve": state.get("physiologicalReserve", 100.0),
        "complication_count": state.get("complicationCount", 0),
        "complication_source": result.get("complicationSource"),
        "complication_cause": result.get("complicationCause"),
        "evaluation": state.get("evaluation"),
        "correct_steps": state.get("correctSteps", 0),
        "total_steps": state.get("totalSteps", 0),
    }


@app.post("/reset")
def reset(req: ResetRequest):
    if req.session_id:
        manager.delete(req.session_id)
    return {"ok": True}


@app.post("/complicate")
def complicate(req: ComplicateRequest):
    session = manager.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        result = session.trigger_complication(req.complication, req.step_index, req.step_label, req.step_kind)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    pending = _sanitize_decision(result["pendingDecision"]) if result["pendingDecision"] else None
    state = session.state
    return {
        "tick": result["tick"],
        "vitals": result["vitalsAfter"],
        "escalation_phase": result["escalationPhase"],
        "procedure_phase": result["procedurePhase"],
        "active_complication": result["activeComplication"],
        "pending_decision": pending,
        "events": result["events"],
        "score": result["score"],
        "completed": state["completed"],
        "mode": state["mode"],
        "physiological_reserve": state.get("physiologicalReserve", 100.0),
        "complication_count": state.get("complicationCount", 0),
        "complication_source": result.get("complicationSource"),
        "complication_cause": result.get("complicationCause"),
        "evaluation": state.get("evaluation"),
        "correct_steps": state.get("correctSteps", 0),
        "total_steps": state.get("totalSteps", 0),
    }


@app.post("/tick")
def tick_session(req: NextRequest):
    session = manager.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        state = session.tick_vitals_only()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    pending = _sanitize_decision(state["pendingDecision"]) if state["pendingDecision"] else None
    return {
        "tick": state["tick"],
        "vitals": state["vitals"],
        "escalation_phase": state["escalationPhase"],
        "procedure_phase": state["procedurePhase"],
        "active_complication": state["activeComplication"],
        "pending_decision": pending,
        "events": state.get("events", []),
        "score": state["score"],
        "completed": state["completed"],
        "mode": state["mode"],
        "physiological_reserve": state.get("physiologicalReserve", 100.0),
        "complication_count": state.get("complicationCount", 0),
        "evaluation": state.get("evaluation"),
        "correct_steps": state.get("correctSteps", 0),
        "total_steps": state.get("totalSteps", 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Procedures / scenarios / search
# ─────────────────────────────────────────────────────────────────────────────


@app.post("/complete")
def complete_session(req: NextRequest):
    session = manager.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session.orchestrator.completed = True
        session.orchestrator.mode = "stock"
        state = session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    pending = _sanitize_decision(state["pendingDecision"]) if state["pendingDecision"] else None
    return {
        "tick": state["tick"],
        "vitals": state["vitals"],
        "escalation_phase": state["escalationPhase"],
        "procedure_phase": state["procedurePhase"],
        "active_complication": state["activeComplication"],
        "pending_decision": pending,
        "events": state.get("events", []),
        "score": state["score"],
        "completed": state["completed"],
        "mode": state["mode"],
        "physiological_reserve": state.get("physiologicalReserve", 100.0),
        "complication_count": state.get("complicationCount", 0),
        "evaluation": state.get("evaluation"),
        "correct_steps": state.get("correctSteps", 0),
        "total_steps": state.get("totalSteps", 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Procedures / scenarios / search
# ─────────────────────────────────────────────────────────────────────────────

def _enrich_scenario(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "specialty": p["specialty"],
        "difficulty": p["category"],
        "thumbnail": f"/thumbnails/{p['id']}.png",
        "tags": [],
        "estimated_time": f"{p.get('totalTicks', 0)} min",
        "anatomy_regions": [],
        "learning_objectives": [],
        "required_instruments": [],
        "category": p["category"],
        "description": p["description"],
        "patient": p["patient"],
        "totalTicks": p["totalTicks"],
        "phases": p["phases"],
    }


@app.get("/procedures")
def procedures():
    procs = list_procedures()
    return {
        "procedures": [
            {
                "id": p["id"],
                "name": p["name"],
                "category": p["category"],
                "specialty": p["specialty"],
                "description": p["description"],
                "patient": p["patient"],
                "totalTicks": p["totalTicks"],
                "phases": p["phases"],
            }
            for p in procs
        ]
    }


@app.get("/scenarios")
def scenarios():
    return {"scenarios": [_enrich_scenario(p) for p in list_procedures()]}


@app.get("/scenarios/{scenario_id}")
def scenario_by_id(scenario_id: str):
    proc = get_procedure(scenario_id)
    if proc is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _enrich_scenario(proc)


@app.get("/procedures/search")
def procedures_search(q: str = Query(default=""), difficulty: Optional[str] = Query(default=None), tag: Optional[str] = Query(default=None)):
    ql = q.lower()
    diff_l = difficulty.lower() if difficulty else None
    tag_l = tag.lower() if tag else None
    out = []
    for p in list_procedures():
        match_text = (p["name"].lower().find(ql) >= 0) or ((p.get("description") or "").lower().find(ql) >= 0)
        match_diff = (p.get("category", "").lower() == diff_l) if diff_l else True
        tags = [t.lower() for t in (p.get("tags") or [])]
        match_tag = (tag_l in tags) if tag_l else True
        if match_text and match_diff and match_tag:
            out.append(p)
    return {"procedures": out}


# ─────────────────────────────────────────────────────────────────────────────
# Evaluate (Groq attending notes) – passthrough stub
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/evaluate")
def evaluate(req: EvaluateRequest):
    # The Node server owns the Groq API key and performs the actual LLM call.
    # This stub simply acknowledges receipt so the legacy contract remains intact
    # if a client ever posts directly. Returns a placeholder note.
    name = req.procedureName or "Unknown Procedure"
    return {
        "notes": f"Direct evaluate passthrough to Scrubin‑Core is not configured. Route through the Node /api/evaluate endpoint for AI attending notes on {name}."
    }


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"core": "up", "sessions": manager.size, "ts": int(time.time() * 1000)}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (mirrors of the TS sanitize functions)
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_decision(d: dict) -> dict:
    return {
        "id": d["id"],
        "tick": d["tick"],
        "phase": d["phase"],
        "phaseLabel": d["phaseLabel"],
        "procedurePhase": d["procedurePhase"],
        "archetype": d["archetype"],
        "prompt": d["prompt"],
        "context": d["context"],
        "options": [{"id": o["id"], "label": o["label"], "archetype": o["archetype"]} for o in d["options"]],
        "urgency": d["urgency"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=os.getenv("SCRUBIN_CORE_HOST", "0.0.0.0"),
        port=int(os.getenv("SCRUBIN_CORE_PORT", "8001")),
        reload=bool(os.getenv("SCRUBIN_CORE_RELOAD", "1") == "1"),
    )
