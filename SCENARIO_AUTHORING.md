# Scenario Authoring Guide

## Overview

ScrubIn Core now uses **data‑driven surgical scenarios** instead of hard‑coded procedure logic.  A *scenario* is a completely immutable definition that describes:

* Patient characteristics
* Operative context (OR setup, positioning, anatomy variants, pathology severity)
* Required resources (instruments, staff, medications, implants, equipment)
* A deterministic **workflow** – an ordered list of immutable step identifiers
* Complications and their deterministic effects
* Success / failure conditions
* Teaching objectives and estimated duration
* Optional **educational metadata** (anatomy explanation, learning objectives, evidence references, etc.) – these fields are UI‑only and are **excluded** from deterministic hashing.

The simulation engine consumes these definitions directly; no `if procedure == …` branching is required.

---

## Adding a New Procedure

1. **Create a scenario definition**
   * Add a new entry in `scrubin/scenarios/registry.py` inside the `_SCENARIOS_LIST`.
   * Use the helper `_simple_scenario` for a minimal definition or construct a full
     `ProcedureScenario` manually if you need custom fields.
2. **Populate required fields**
   ```python
   ProcedureScenario(
       id="lap_appendectomy",               # Unique identifier (used for look‑up & hashing)
       display_name="Laparoscopic Appendectomy",
       specialty="General Surgery",
       difficulty="moderate",
       description="Removal of the appendix via laparoscopy.",
       patient=PatientInfo(...),
       operative_context=OperativeContext(...),
       resources=Resources(...),
       workflow=(Step(id="establish_access"), Step(id="identify_target"), ...),
       complications=(),
       success_conditions=("completed",),
       failure_conditions=("critical_error",),
       teaching_objectives=("identify appendix", "manage intra‑abdominal infection"),
       estimated_duration_minutes=60,
       educational={
           "anatomy_explanation": "Appendix lies at the blind‑ending of the caecum.",
           "common_mistakes": "Incorrect trocar placement can injure the bowel.",
       },
   )
   ```
3. **Maintain deterministic ordering**
   * The registry builds a mapping sorted by scenario ID, guaranteeing deterministic
     iteration order.
   * Do **not** rely on filesystem ordering; all scenarios are defined in code.
4. **Run validation**
   * The `ScenarioRegistry` validates each scenario on construction.  If you
     introduce duplicate step IDs, missing fields, or negative duration values,
     a `ScenarioValidationError` will be raised.
5. **Commit**
   * Push the updated `registry.py`.  No changes to simulation engine code are
     required.

---

## Deterministic Hashing

* Each `ProcedureScenario` implements `deterministic_hash()` – it serialises only the
  fields that affect replay (UI‑only `educational` data is omitted).
* The registry provides `deterministic_hash()` for the **entire library**, which
  concatenates the per‑scenario hashes in alphabetical order of scenario ID and
  hashes the result with SHA‑256.
* These hashes are used by the replay system to guarantee that identical scenario
  sets produce identical simulation traces.

---

## OR Team Engine

### Team Role Definitions

`TeamRole` dataclass defines immutable role identifiers used by the deterministic
engine.  Fields:

* `id` – Unique deterministic identifier.
* `role_type` – Role type (e.g., `PrimarySurgeon`, `ScrubNurse`, `Anesthesiologist`).

Roles are listed in the `team_roles` tuple of a `ProcedureScenario`.  These static
definitions are included in the scenario’s deterministic hash.

### Task Assignment & Instrument Handling

The `TeamTaskEngine` assigns workflow steps to the first available member of each
required role (`required_roles` on a `Step`).  It also verifies that required
instruments are `available` and produces deterministic events:

* `InstrumentRequested`
* `InstrumentAcknowledged`
* `InstrumentInUse`
* `TaskAssigned`
* `TaskCompleted`

Instrument state is tracked by the immutable `InstrumentState` with statuses
`available`, `in_use`, `contaminated`, `unavailable`, `dropped`, `missing`.

### Communication Events

Simple deterministic communication events model OR messaging:

* `request` → `request` type (e.g., `InstrumentRequested`).
* `acknowledgment` → `InstrumentAcknowledged`.
* `warning`, `confirmation`, `escalation`, `timeout` are emitted as needed
  by the engine (future extensions).

All communication is stored in an append‑only event log and participates in
replay verification.

### Workflow Synchronisation

Steps may specify `required_roles` and `required_instruments`.  The workflow
engine blocks progression until all prerequisites, role availability, and
instrument readiness are satisfied, guaranteeing deterministic ordering.

### Failure States

Deterministic failure events include:

* `TaskFailed` (missing role, unavailable instrument)
* `InstrumentFailed` (instrument missing, contaminated, etc.)

These are emitted with a `reason` field and halt the step.

### Replay Guarantees

* All dataclasses are frozen; updates use `replace`.
* Event logs are append‑only.
* IDs and hashes are deterministic (SHA‑256 of canonical JSON).
* No wall‑clock timing, randomness, or unordered iteration is used.

## Testing

* Tests verify that the registry loads all scenarios, validates them, and that the
  combined hash remains stable across runs.
* When adding a new scenario, run the test suite (`pytest -q`) to ensure no
  validation errors are introduced.

---

**Remember:** Scenario definitions are *data only*.  Any procedural behavior must be
expressed through the deterministic workflow steps and associated complication
logic, not by adding code to the engine.
