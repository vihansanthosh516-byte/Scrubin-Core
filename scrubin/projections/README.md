# Projections

The ScrubIn core uses a CQRS-style architecture where the read-side is decoupled from the write-side using Projections.

## CQRS-style split

The `EventLedger` serves as the single source of truth for the system (append-only write-side). To answer queries, the `SimulationService` routes requests to in-memory projections instead of scanning the ledger.

## Write-side vs Read-side

- **Write-side**: Handled by the `Orchestrator` and `ActionAuthority`. They emit events onto the `EventBus`, which logs them to the `EventLedger`.
- **Read-side**: Handled by the `StateProjection`, `DecisionProjection`, and `EventProjection`. They subscribe to ledger events and incrementally update their optimized read models.

## Projection Update Guarantees

Projections are updated incrementally and synchronously immediately after an event is logged. Projections are read-only and never mutate the ledger history.

## Deterministic Ordering Guarantees

Events are processed in a strict sequence determined by `sequence_id` assigned by the `EventBus`. This ensures projections are deterministic and will always rebuild to the exact same state given the same event history.

## WebSocket Replay Guarantees

Clients can reconnect and request missed events using the `after_sequence` parameter. The `EventProjection` maintains a bounded history of events in memory, enabling gapless stream replay without ledger scans.

## Event Cursor Semantics

Event cursors (`sequence_id`) are monotonically increasing integers. They act as logical timestamps for state changes. WebSockets and API endpoints return the sequence IDs to allow clients to track their sync state.
