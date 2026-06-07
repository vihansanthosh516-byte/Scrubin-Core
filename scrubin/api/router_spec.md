# Router Specification (Placeholder)

The concrete HTTP routing (FastAPI, Flask, etc.) will be defined later.
Below is a high‑level description of the intended endpoints and their
corresponding request/response contracts.

```
POST   /api/simulation/create          → SimulationCreateRequest
GET    /api/simulation/{session_id}/state   → SimulationStateResponse
POST   /api/simulation/{session_id}/action → SimulationActionRequest
```

* **Create** – Returns ``SimulationCreateResponse`` with a new ``session_id``
  and the immutable initial ``WorldState``.
* **State** – Returns ``SimulationStateResponse`` containing the current tick,
  timeline events, scores, and summary snapshots.
* **Action** – Accepts ``SimulationActionRequest`` and returns
  ``SimulationActionResponse`` after applying the deterministic placeholder
  action (future implementation will invoke the full cognition pipeline).

All routes are pure; they never expose mutable objects to the client.
