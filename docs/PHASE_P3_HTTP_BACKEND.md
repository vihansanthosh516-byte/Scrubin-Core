# Phase P.3 – HTTP Backend Service

## Goal
Expose the deterministic **Session Manager** and **Persistent Session Store** via a thin, framework‑agnostic HTTP API.  The API must be a pure wrapper – all simulation logic stays in the immutable core (Phase P.2) and no additional randomness is introduced.

## Architecture
```
Browser ⇆ HTTP API (FastAPI) ⇆ API contracts ⇆ SessionManager ⇆ PersistentSessionStore ⇆ Scrubin Core ⇆ WorldState
```
* The HTTP layer only translates JSON payloads to the internal dataclass contracts.
* Responses return immutable dataclasses that FastAPI serialises deterministically.
* Errors are modelled as immutable dataclasses for consistent, reproducible error payloads.

## Endpoints
| Method | Path | Purpose | Request model | Response model |
|---|---|---|---|---|
| **POST** | `/session/create` | Create a new simulation session. | `CreateRequestModel` (`seed`, `initial_tick`) | `SimulationCreateResponse` (`session_id`, `initial_world_state`) |
| **GET** | `/session/{session_id}/state` | Retrieve the current immutable simulation state. | – | `SimulationStateResponse` |
| **POST** | `/session/{session_id}/action` | Execute one deterministic action step. | `ActionRequestModel` (`action_type`, `parameters`, `timestamp`) | `SimulationActionResponse` |
| **POST** | `/session/{session_id}/save` | Persist the current world state. | – | `{ "metadata": SessionMetadata }` |
| **POST** | `/session/{session_id}/load` | Load the persisted state back into the in‑memory manager. | – | `{ "metadata": SessionMetadata, "state": SimulationStateResponse }` |
| **DELETE** | `/session/{session_id}` | Delete a persisted session (and its in‑memory entry). | – | `{ "detail": "Session <id> deleted" }` |
| **GET** | `/sessions` | List all persisted session identifiers (sorted). | – | `List[str]` |

## Validation & Errors
All validation errors, missing sessions, and persistence I/O errors are reported using immutable error models:
* `APIError` – base model (`message`, optional `code`).
* `ValidationError` – malformed request payloads.
* `SessionNotFoundError` – unknown session identifiers.
* `PersistenceError` – I/O or JSON (de)serialization problems.

FastAPI exception handlers translate these dataclasses into JSON responses with appropriate HTTP status codes (404, 422, 500).

## Replay Guarantee
The API never introduces nondeterminism:
* The same request sequence against the same persisted session always yields the same JSON response.
* Session identifiers are opaque UUIDs; they are not derived from request content.
* All state transitions are performed by the core `SessionManager`/`PersistentSessionStore`, which rely solely on deterministic logic and the deterministic `SimulationRNG`.

## Deployment Sketch
```
Cloudflare Pages (static) → FastAPI ASGI app → Oracle VM (or any compute) → Scrubin Core
```
The server can be containerised and deployed behind any HTTP gateway (e.g., Cloudflare Workers, AWS ALB) without code changes because the routing logic is framework‑agnostic.

## Testing
Deterministic unit tests (see `tests/test_http_backend.py`) cover:
* Session creation, retrieval, action execution.
* Persistence (save/load) and deletion.
* Listing sessions.
* Error handling for unknown sessions and malformed bodies.
* Replay consistency – a saved‑then‑loaded session followed by an action produces the exact same world state as a continuous run.

All tests run in under a second and rely only on the in‑process FastAPI `TestClient`.

---
*No authentication, rate‑limiting, or external services are introduced at this layer – the focus remains on a deterministic, testable API surface.*
