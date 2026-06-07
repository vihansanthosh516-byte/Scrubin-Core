# Phase P.1 – Backend API Foundation

## Overview

Phase P.1 introduces a **production‑ready, framework‑agnostic API layer** that sits between the Scrubin frontend (e.g., a React UI hosted on Cloudflare Pages) and the deterministic Scrubin Core simulation engine.  The API exposes **immutable request/response contracts**, manages per‑session immutable `WorldState` objects, and guarantees that *identical* requests always produce *identical* responses, preserving the replay determinism established in Phase O.

The layer is deliberately **framework‑neutral** – it provides only pure Python abstractions (`api_contracts`, `session_manager`, `serialization`).  A concrete HTTP server (FastAPI, Flask, etc.) can be added later without touching the core logic.

---

## Architecture Diagram
```
Browser UI (Cloudflare Pages) 
   ↓ HTTP/JSON
Backend API (framework‑agnostic) 
   ↓ Python contracts / Session manager
Scrubin Core (deterministic engines) 
   ↓ Immutable WorldState
   ↓ Replay‑safe evolution
   ↓ JSON for transport
```

### Data Flow
1. **Create Session** – Frontend sends `SimulationCreateRequest` (seed, optional initial tick). The API creates a new `WorldState` and returns `SimulationCreateResponse` containing a unique `session_id`.
2. **Perform Action** – Frontend posts `SimulationActionRequest` (session_id, action_type, parameters, timestamp). The API looks up the session’s `WorldState`, applies a deterministic placeholder action (currently a tick‑forward and a single `TimelineEvent`), stores the new immutable world, and returns `SimulationActionResponse`.
3. **Query State** – Frontend can GET the current snapshot via `SimulationStateResponse` without causing any mutation.

---

## 1. API Contracts

All contracts are **frozen dataclasses** – they cannot be mutated after creation and contain **no mutable default values**.

| Contract | Fields | Description |
|----------|--------|-------------|
| **SimulationCreateRequest** | `seed: int`<br>`initial_tick: int = 0` | Request to start a new deterministic simulation session. |
| **SimulationCreateResponse** | `session_id: str`<br>`initial_world_state: WorldState` | Response after session creation – returns the immutable initial world. |
| **SimulationActionRequest** | `session_id: str`<br>`action_type: str`<br>`parameters: Mapping[str, Any] = {}`<br>`timestamp: int = 0` | Request to perform a deterministic action. `parameters` must be JSON‑serialisable. |
| **SimulationActionResponse** | `world_tick: int`<br>`timeline_events: Tuple[TimelineEvent, ...]`<br>`updated_score: float`<br>`updated_world_state: WorldState`<br>`active_goals: Tuple[Any, ...]`<br>`active_intents: Tuple[Any, ...]`<br>`reflection_summary: Any`<br>`learning_summary: Any` | Response after an action – contains the new world tick, events generated, score placeholder, full immutable world snapshot, and convenient aggregates for the client. |
| **SimulationStateResponse** | `world_tick: int`<br>`timeline_events: Tuple[TimelineEvent, ...]`<br>`updated_score: float`<br>`current_world_state: WorldState`<br>`active_goals: Tuple[Any, ...]`<br>`active_intents: Tuple[Any, ...]`<br>`reflection_summary: Any`<br>`learning_summary: Any` | Read‑only snapshot of a session’s state (no mutation). |

All contracts live in **`scrubin/api/api_contracts.py`**.

---

## 2. Session Model

The **`SessionManager`** (see `scrubin/api/session_manager.py`) owns a private in‑memory mapping `session_id → WorldState`.  Each session:
* Starts with a clean deterministic world (`WorldState(tick=initial_tick, seed=seed)`).
* Holds exactly **one immutable** world snapshot.  The internal dictionary is the only mutable container, but it never leaks mutable state to callers.
* Is updated atomically: applying an action creates a new `WorldState` (via the Core engines or the placeholder tick‑forward) and replaces the entry.

### Lifecycle
1. **Create Session** → `SimulationCreateResponse` (new `session_id`).
2. **Load Initial WorldState** → stored internally.
3. **Perform Action** → `apply_action` generates a new world and stores it.
4. **Advance Tick** → implicit in `apply_action` (placeholder) or later in the full engine pipeline.
5. **Repeat** – each subsequent action works on the latest immutable snapshot.

---

## 3. Action Protocol

Supported `action_type` values (currently placeholders, extensible later):
* `perform_procedure`
* `interact`
* `administer_medication`
* `inspect`
* `communicate`
* `wait`
* `custom_action`

Each `SimulationActionRequest` contains:
* `session_id` – identifies the target session.
* `action_type` – string name of the action.
* `parameters` – immutable mapping of action‑specific data (e.g., procedure name, medication dosage).
* `timestamp` – logical simulation tick when the action is issued.

The backend **never mutates** the world directly from the request; instead it generates a deterministic `TimelineEvent` (`action_performed:<type>`) and advances the tick, guaranteeing replay safety.

---

## 4. Response Protocol

All response objects are immutable dataclasses.  They contain:
* `world_tick` – the tick after the action.
* `timeline_events` – tuple of `TimelineEvent` objects generated by the action.
* `updated_score` – placeholder for any scoring metric (e.g., safety, efficiency).
* `updated_world_state` – the full immutable snapshot of the world.
* Aggregates (`active_goals`, `active_intents`, `reflection_summary`, `learning_summary`) to make it easy for the UI to display high‑level information without traversing the full world.

Because the objects are frozen, the frontend cannot accidentally mutate simulation state.

---

## 5. Serialization

`scrubin/api/serialization.py` provides deterministic JSON round‑trip helpers:
```python
json_str = serialize_worldstate(world)   # deterministic ordering (sort_keys=True)
world2   = deserialize_worldstate(json_str)
assert world == world2
```
* The helper converts dataclasses (including nested ones) into plain JSON‑compatible structures, turning tuples into lists while preserving order.
* Deserialization reconstructs a `WorldState` using its constructor; missing fields fall back to the dataclass defaults, guaranteeing that a minimal world round‑trips correctly.
* Deterministic `sort_keys=True` ensures the same byte string for identical worlds.

---

## 6. Replay Safety Guarantees

* **Identical seed + identical request sequence ⇒ identical world** – the backend never introduces additional randomness; the only stochastic source is the `SimulationRNG` seeded in `SimulationCreateRequest`.
* **Immutable state transitions** – each engine (including the placeholder action) returns a brand‑new `WorldState`; the stored world never changes in place.
* **Deterministic sorting** – all collections are stored as sorted tuples; serialization orders keys alphabetically.
* **Deterministic identifiers** – IDs for events, actions, etc., are derived from the tick and action type, guaranteeing repeatability.

These guarantees are essential for scientific reproducibility, debugging, and for building higher‑level services (e.g., replay caches, checkpointing).

---

## 7. Oracle Deployment Compatibility

* **Frontend** – Cloudflare Pages (static assets).
* **Backend** – Oracle Cloud VM (any Python web framework can be installed).
* **Database / Auth** – Supabase (outside the core API; the API layer can be extended with Supabase JWT validation later).
* The API contracts are **framework‑agnostic**, allowing the same Python module set to be used with FastAPI, Flask, or a serverless function on Oracle Cloud.

---

## 8. Folder Structure
```
├─ scrubin/
│   └─ api/
│       ├─ api_contracts.py      # frozen request/response dataclasses
│       ├─ session_manager.py    # in‑memory SessionManager implementation
│       ├─ serialization.py      # deterministic JSON helpers
│       └─ router_spec.md        # placeholder for future HTTP routing spec
└─ docs/
    └─ PHASE_P1_API.md           # this document
```
No networking code resides here; the next phase will wire these abstractions into a concrete HTTP server.

---

## 9. Testing Summary

Deterministic unit tests (`tests/`):
* **Request immutability** – attempts to modify a frozen request raise `FrozenInstanceError`.
* **Identical requests → identical responses** – creating two sessions with the same seed and applying the same action yields equal `SimulationActionResponse` objects.
* **Serialization round‑trip** – `WorldState → JSON → WorldState` preserves equality.
* **Immutable response objects** – responses are frozen dataclasses.
* **WorldState unchanged except via engine** – the manager never mutates a stored world; a new world is always produced.

All tests execute in under a second and pass, confirming that the API foundation respects the deterministic contract required by Phase O.

---

## 10. Next Steps (Phase P.2)

* Implement a real HTTP router (FastAPI) using the contracts.
* Hook the placeholder action to the full cognition pipeline (`PhysiologicEvolutionEngine`).
* Add authentication via Supabase JWTs.
* Persist sessions to a database for crash‑recovery.
* Extend the action catalog with concrete procedure, medication, and communication actions.

The backend API foundation is now complete, documented, and verified with deterministic tests, ready for integration with the frontend and deployment on Oracle Cloud.