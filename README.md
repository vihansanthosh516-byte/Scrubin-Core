# scrubin-core

A deterministic clinical-simulation orchestration engine. It models a surgical
patient through ticks of evolving physiology, complications, procedures, and
cognition, then self-tests the run, diagnoses root causes, and proposes logic
patches — all reproducible from a seed. Built for surgical-simulation training,
benchmarking, and self-improvement research.

## Architecture

The engine is layered as a tick-driven pipeline. Each tick, an **Orchestrator**
dispatches events through a bus to **Agents** (vitals, complications, procedures,
decision), evolves an immutable **WorldState** via **Engines**, and runs a deep
**Cognition cascade** (belief → meta → executive → strategies → policy). A
**Projection** layer derives snapshots for the API; a **Tester/Improvement**
loop scores runs and emits patches.

```
main.py / API (FastAPI)
        │
        ▼
 SimulationService  ──▶  Orchestrator ──tick()──▶  EventBus ──▶ Agents
        │                       │                                 │
        │                       ▼                                 ▼
   Projections              WorldState (immutable)           Complications
  (state/event/decision)    Physiology / Procedure /          Procedures
        │                   Cognitive / Scoring / Anatomy /    Decision (MCTS)
        ▼                   Biology / Knowledge Graph ...
   SessionManager + PersistentSessionStore (JSON)              Cognition cascade
        │                                                          (belief→meta→
        ▼                                                           executive→strat→policy)
   HTTP / WebSocket API
        │                                                          │
        ▼                                                          ▼
   Frontend                                              Tester (checks) → ImprovementEngine
                                                        (structure/physiology/causality/recovery)
                                                                │
                                                                ▼
                                                         PatchExecutor (apply + rerun)
```

### Key modules (`scrubin/`)

- **`core/`** — `Orchestrator`, `EventBus`, `ConfigLayer`; the tick driver.
- **`world/`** — `WorldState` (immutable frozen dataclass), `SimulationWorld`
  (legacy mutable model), `HospitalWorld`, system-coupling graph.
- **`physiology/`, `anatomy/`, `biology/`** — organ subsystems, trajectories,
  homeostasis, tissue healing, metabolism, contamination.
- **`patient/`** — patient profiles and variants (`PATIENT_PROFILES`).
- **`procedures/`** — data-driven procedure registry (YAML-driven), compiled
  into `ProcedurePhase`s by `engine/procedural_phase_engine.py`.
- **`decision/`** — MCTS planner, dynamic actions, consequence engine,
  validators, forecast, policy decomposition.
- **`cognition/`** — belief/formation/validation, meta-learning, executive
  goals, strategies, arbitration, reflection (all deterministic & hashed).
- **`events/`** — `SurgicalEvent` ledger + immutable `event_processor`.
- **`replay/`** — snapshot engine + deterministic world hashing (JSON, not pickle).
- **`counterfactual/`, `causal/`** — fork/replay and causal-stability gates.
- **`tester/`** — `TestRunner`, stress profiles, checks, `ScoreEngine`.
- **`improvement/`** — `ImprovementEngine` (root-cause analysis → patches),
  `PatchExecutor` (apply & rerun), `diff_renderer`.
- **`rl/`** — gym-style `ScrubInEnv`, rollout runner, reward shaping.
- **`api/`** + **`server/`** — two FastAPI surfaces (see Security below).
- **`auth/`** — `UserIdentity` + `get_current_user` dependency.
- **`audit/`, `governance/`, `safety/`, `validation/`** — guardrails & audit.
- **`adaptive/`, `learning/`, `knowledge/`, `memory/`** — tutoring, curriculum,
  benchmarks, episodic memory (JSON-compressed), ontology graphs.

## Security model

**Authentication** — `get_current_user` resolves the caller via the
`Authorization: Bearer <user_id>` header. Mode is governed by `SCRUBIN_AUTH_MODE`:

- `dev` (default) — treats `Bearer <user_id>` as the identity, falling back to
  `default_user` when no header is present. **Never use in production.**
- `jwt` — fail-closed production mode that requires a real JWT verifier
  (`SCRUBIN_JWKS_URL`) to be plugged into `_authenticate_jwt`.

**Authorization** — session endpoints enforce ownership via `_owned_session`
(reads the in-memory `_owners` map on `SessionManager`, defaulting to
`default_user` for legacy sessions). Cross-user access returns **403**. The
WebSocket endpoint resolves the caller *before* accepting the handshake and
closes with code `4401`/`4403` on auth/ownership failure.

**CORS** — origins are read from `SCRUBIN_ALLOWED_ORIGINS` (comma-separated);
`allow_credentials=True` is paired with an explicit allowlist only (never `*`).

**Persistence safety** — `PersistentSessionStore` validates `session_id` against
`^[A-Za-z0-9_-]{1,64}$` to prevent path traversal. Snapshots and episodic memory
are serialized as **JSON** (not pickle), so stored blobs cannot trigger
arbitrary code execution on load.

## Getting started

### Install

```bash
python -m pip install -r requirements.txt
python -m pip install pytest pytest-timeout ruff pip-audit httpx httpx2
```

### Run the self-improvement loop (CLI)

```bash
python main.py
```

Runs five stress profiles (`default`, `hypoxia`, `broken_procedure`,
`recovery_suppression`, `causality_race`), scores each run, diagnoses root
causes, and applies/reruns patches.

### Run the API server

```bash
python -m scrubin.api          # serves scrubin.api.server:app on :8000
```

Protected contract API (owned by `scrubin/server`):

```bash
python -c "import scrubin.server.app as a; import uvicorn; uvicorn.run(a.app, host='0.0.0.0', port=8000)"
```

Key endpoints: `POST /session/start`, `POST /session/tick`,
`POST /session/decide`, `GET /session/state`, `GET /session/summary`,
`GET /procedures`, `/profiles`, and `WS /session/{id}/ws`.
All session-touching endpoints require `Authorization: Bearer <user_id>`.

### Tests

```bash
PYTHONPATH=. pytest -q --timeout=12 -o addopts=""
```

### CI gates (determinism & integrity)

```bash
PYTHONPATH=. python ci/gates/policy_fingerprint_gate.py
PYTHONPATH=. python ci/gates/system_lock_gate.py
PYTHONPATH=. python ci/gates/replay_determinism_gate.py
PYTHONPATH=. python ci/gates/counterfactual_stability_gate.py
PYTHONPATH=. python ci/gates/api_isolation_gate.py
```

CI (`.github/workflows/scrubin_phase16_ci.yml`) runs the five gates plus
`ruff`, `pytest`, and `pip-audit`.

## Configuration via environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SCRUBIN_API_URL` | `http://localhost` | API base URL for `client.py` |
| `SCRUBIN_TIMEOUT` | `30` | HTTP timeout for `client.py` |
| `SCRUBIN_AUTH_MODE` | `dev` | `dev` (bearer-as-id) or `jwt` (fail-closed) |
| `SCRUBIN_JWKS_URL` | _(empty)_ | JWKS endpoint required when `AUTH_MODE=jwt` |
| `SCRUBIN_ALLOWED_ORIGINS` | localhost dev origins | CORS allowlist |

## Notes

- The legacy frontend-facing `api/server:app` and the protected `server/app.py`
  coexist; both enforce auth. Prefer `server/app.py` for new integrations.
- Determinism is a first-class contract: every cognition record carries a
  `replay_hash` over canonical JSON, and the replay gates assert bit-identical
  re-runs from a seed.
