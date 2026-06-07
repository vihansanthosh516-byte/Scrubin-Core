# Project Status Report

## Completed Phases
- **Phase P.2 – Persistent Session Store**: Implemented deterministic JSON session persistence with metadata versioning and SHA‑256 world hashing.
- **Phase P.3 – HTTP Backend (FastAPI)**: Exposed CRUD‑style endpoints for session lifecycle, actions, save/load, deletion, and session listing. Added global error handling and immutable response models.
- **Phase P.4 – Authentication & Ownership Layer**:
  - Introduced immutable `UserIdentity` dataclass.
  - Added placeholder JWT‑based authentication dependency (`get_current_user`).
  - Stored `owner_user_id` in session metadata and enforced ownership on every endpoint (403 Forbidden on violation).
  - Updated `SessionManager` to track in‑memory owners.
  - Added authorization error model and handler.

---

## Architecture Diagram
```mermaid
flowchart TD
    Browser --> Auth[Supabase JWT (placeholder)]
    Auth --> HTTP[FastAPI Backend]
    HTTP --> SM[SessionManager (in‑memory)]
    HTTP --> PS[PersistentSessionStore (disk JSON)]
    SM --> Engine[Deterministic Simulation Engine]
    Engine --> WorldState[WorldState (immutable)]
    PS -->|load/save| WorldState
```

---

## Active Engine Pipeline
1. **`SessionManager.create_session`** – creates a fresh `WorldState` (seed + initial tick).
2. **`apply_action`** – deterministic placeholder: creates a `TimelineEvent`, appends it, ticks forward.
3. **`get_state`** – returns a `SimulationStateResponse` containing the current `WorldState` and convenient aggregates.
4. **Persistence** – `save_session`/`load_session` serialize/deserialize the `WorldState` deterministically (sorted keys, compact separators) and compute a stable SHA‑256 hash.

---

## HTTP Endpoints (FastAPI)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session/create` | Create a new session (owner = authenticated user). |
| `GET`  | `/session/{session_id}/state` | Retrieve the current snapshot of a session. |
| `POST` | `/session/{session_id}/action` | Apply a deterministic action to a session. |
| `POST` | `/session/{session_id}/save` | Persist the current session state to disk. |
| `POST` | `/session/{session_id}/load` | Load a persisted session into memory (owner validated). |
| `DELETE`| `/session/{session_id}` | Delete both in‑memory and persisted representation. |
| `GET`  | `/sessions` | List **only** the sessions owned by the caller. |

---

## Persistence Architecture
- **File Layout**: `scrubin/api/sessions/<session_id>.json`
- **Metadata** (`SessionMetadata`):
  - `session_id`
  - `created_at_tick`
  - `last_saved_tick`
  - `simulation_seed`
  - `version`
  - `owner_user_id`
  - `world_hash` (SHA‑256 of the serialized world)
  - `schema_version`
- **Operations**:
  - `create_session(session_id, initial_state, owner_user_id)`
  - `save_session(session_id, state, owner_user_id)` (preserves existing owner)
  - `load_session(session_id)` returns `(WorldState, SessionMetadata)`
  - `list_sessions_for_user(user_id)` filters by `owner_user_id`

---

## Replay Determinism Guarantees
- **Deterministic Serialization** – JSON written with `sort_keys=True` and compact separators.
- **World Hash** – SHA‑256 hash of the serialized world ensures integrity and fast change detection.
- **Stateless Action Application** – `apply_action` uses only the current immutable `WorldState` and the supplied action, guaranteeing identical results for identical action streams.
- **Full‑stack Tests** – End‑to‑end HTTP tests verify that a saved‑then‑loaded session reproduces the exact same state, and that two independent runs with the same seed/action sequence converge.

---

## Test Summary
- **Total tests**: **386**
- **Passing**: 386 / 386
- **Coverage**: Critical paths exercised (session lifecycle, persistence, ownership, replay determinism).

---

## Known Technical Debt
- Placeholder authentication only parses `Authorization: Bearer <user_id>`; no JWT verification, expiration handling, or role checks.
- Ownership validation performs a second metadata read on every request (could be cached or indexed).
- `PersistentSessionStore.list_sessions_for_user` iterates over all session files; may not scale to very large numbers of sessions.
- The engine still uses a **placeholder** deterministic action implementation – real cognition pipeline is not yet integrated.
- `SessionManager.set_state` still overwrites the owner if `owner_user_id` is supplied; callers must ensure consistency.

---

## Recommended Next Phase (P.5)
1. **Full Supabase JWT Integration** – verify signatures, extract full user profile, handle token expiration.
2. **Replace Placeholder Action Engine** with the actual cognition pipeline while preserving deterministic guarantees.
3. **Optimization of Persistence Layer** – index metadata (e.g., SQLite or key‑value store) to make ownership queries O(1) and support pagination.
4. **Add Auditing & Security Logging** – record ownership mismatches, failed auth attempts, and mutation events.
5. **Scalability Tests** – benchmark session creation, save/load performance with thousands of sessions.
6. **Document Deployment** – include Cloudflare Workers → Oracle VM deployment guide for the full stack.

---

*Generated by OpenCode – the autonomous coding assistant.*