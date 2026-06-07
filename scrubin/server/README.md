# Scrubin HTTP Backend (Phase P.3)

This module implements a **framework‑agnostic** HTTP API layer for the Scrubin Core simulation engine.  The implementation uses **FastAPI** as a thin wrapper, but the business logic resides entirely in the existing immutable core components:

* `SessionManager` – in‑memory deterministic session handling.
* `PersistentSessionStore` – deterministic JSON persistence (Phase P.2).
* API contract dataclasses (`api_contracts.py`) – immutable request/response models.

The server exposes a minimal set of endpoints that translate HTTP requests into calls on these back‑end objects, preserving the deterministic replay guarantees of the core.  No additional state, randomness, or cognition logic is introduced at this layer.

## Layout
```
scrubin/server/
├─ app.py                 # FastAPI application entry‑point
├─ routes.py              # All endpoint definitions
├─ dependency_provider.py # Singleton providers for SessionManager & store
├─ error_models.py        # Immutable error dataclasses
└─ README.md              # This file
```

The code is deliberately lightweight and can be swapped for any ASGI‑compatible framework without changing the core business logic.
