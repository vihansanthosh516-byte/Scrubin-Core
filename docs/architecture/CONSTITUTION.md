# ScrubIn Architecture Constitution (v1.0)

## 1. System Philosophy
ScrubIn is a multi-layer deterministic clinical simulation operating system. It enforces strict separation between orchestration, verification, simulation physics, and intelligence.

## 2. Layer Definitions

### Layer 1: Control Plane (Orchestration)
- **Role**: intent → jobs → scheduling.
- **Boundary**: No clinical logic, no physiological mutation, no MCTS execution.
- **Modules**: `scrubin/control_plane/kernel.py`, `jobs.py`, `scheduler.py`.

### Layer 2: Verification Layer (Truth & Safety)
- **Role**: Formal constraint enforcement.
- **Boundary**: Acts as a hard gate before any code reaches the Core.
- **Modules**: `scrubin/control_plane/validation/`, `schema_registry.py`, `contract_validator.py`, `runtime_guard.py`.

### Layer 3: Core Simulation Engine (Physics)
- **Role**: Deterministic evolution of physiological reality.
- **Boundary**: Immutable from outside; only internal physics models mutate state.
- **Modules**: `scrubin/world/`, `scrubin/clinical/`, `scrubin/decision/mcts.py`.

### Layer 4: Learning & Intelligence
- **Role**: Policy optimization and evaluation.
- **Boundary**: Observes state, suggests policies, never mutates world directly.
- **Modules**: `scrubin/learning/`, `scrubin/agents/`.

### Observability & Intelligence Invariants
- **OBS-001**: Observability remains strictly read-only.
- **OBS-002**: All stream events require registered and versioned schemas.
- **OBS-003**: All distributed events MUST carry trace correlation IDs.
- **OBS-004**: Replay streams must remain deterministic even under semantic compression.
- **OBS-005**: Semantic analysis tools MUST NOT mutate execution ordering or physiology.

1. **Core Purity**: Core simulation MUST NOT depend on Control Plane logic.
2. **Verification Precedes Execution**: No job reaches the Core without passing Schema + Contract validation.
3. **Deterministic Replay**: Any state at tick T must be reconstructible from (initial state + event log).
4. **No Cross-Layer Mutation**: Only the Core Engine can mutate physiological state.
5. **Observability Integrity**: Every job must leave a cryptographic audit trail (Phase 12.1).

## 4. Execution Lifecycle
1. **Intent** (ExperimentConfig)
2. **Job Generation** (JobManager)
3. **Formal Validation** (RuntimeVerificationLayer)
4. **Execution Plan Approval** (RuntimeGuard)
5. **Core Execution** (SimulationKernel)
6. **State Capture** (SnapshotManager)
7. **Audit Chain Update** (ExecutionAuditChain)
8. **Policy Feedback** (OnlineLearner)
