# Scrubin Procedure Authoring Framework

## Overview
This document defines the **authoring model** for adding new surgical procedures to Scrubin without touching engine code.  All clinical logic (phases, decision cards, anatomy, instruments, complications, scoring, exit criteria) is expressed as **immutable JSON** files that are loaded at runtime by the **Universal Surgical Engine** in `scrubin‑core`.  The shared physiology engine (bleeding, oxygen debt, shock, infection, anesthesia, medications, inflammation, replay, persistence, optimisation) remains unchanged.

---

## 1. Directory Structure (within `scrubin-core/scrubin/procedures/`)
```
scrubin-core/
└─ scrubin/
   └─ procedures/
      ├─ <procedure_name>/               # e.g. appendectomy/, cabg/, trauma/
      │   ├─ config.json                 # global settings for the procedure
      │   ├─ phases.json                 # ordered list of phase objects
      │   ├─ anatomy.json                # anatomical structures referenced by cards
      │   ├─ instruments.json            # instrument catalog (or reference shared catalog)
      │   ├─ cards.json                  # array of decision‑card objects (graph edges)
      │   ├─ complications.json        # complication definitions and triggers
      │   └─ scoring.json                # scoring rules, outcome weights, exit criteria
      ├─ ... (additional procedures)    
      └─ plugins/                       # optional Python modules for custom hooks
          ├─ __init__.py
          ├─ appendectomy.py            # custom_decision_engine, post_tick, etc.
          └─ <procedure_name>.py        # optional per‑procedure pure functions
```

*All JSON files must be **immutable** – they are never mutated at runtime.  The engine caches their contents on first load.*

---

## 2. JSON Schemas (canonical)**
### 2.1 `config.json`
```json
{
  "procedure_id": "appendectomy",
  "display_name": "Laparoscopic Appendectomy",
  "difficulty": "Beginner",
  "default_stress_profile": "MedicalStudent",
  "estimated_duration_minutes": 45,
  "category": "General",
  "specialty": "General Surgery"
}
```
*Provides metadata used by the UI procedure library and by the engine for seeding stress‑profile parameters.*

### 2.2 `phases.json`
```json
[
  {"id": "phase_entry", "name": "Entry", "description": "Gain safe access to the abdominal cavity"},
  {"id": "phase_exposure", "name": "Exposure", "description": "Identify the appendix"},
  {"id": "phase_division", "name": "Division", "description": "Clip and cut the appendix"},
  {"id": "phase_closure", "name": "Closure", "description": "Secure stump and close ports"}
]
```
*Phases are ordered but the engine treats them as nodes – cards can transition to any later phase, enabling branching.*

### 2.3 `anatomy.json`
```json
{
  "structures": [
    {"id": "cecum", "name": "Cecum", "type": "organ"},
    {"id": "appendix", "name": "Appendix", "type": "organ"},
    {"id": "mesoappendix", "name": "Mesoappendix", "type": "ligament"}
  ]
}
```
*Provides a lookup for `anatomical_targets` used in decision cards.*

### 2.4 `instruments.json`
```json
{
  "instruments": [
    {"id": "grasper", "name": "Laparoscopic Grasper"},
    {"id": "clip_applier", "name": "Clip Applier"},
    {"id": "scissors", "name": "Laparoscopic Scissors"},
    {"id": "suction", "name": "Suction Device"}
  ]
}
```
*Shared catalog – procedures may reference any instrument listed here.*

### 2.5 `cards.json` (core element)
Each entry is an **immutable decision card** that forms a directed edge in the procedural graph.
```json
[
  {
    "id": "appendix_expose_01",
    "phase": "phase_exposure",
    "title": "Follow Taenia Coli",
    "description": "Trace the tenia coli to locate the base of the appendix.",
    "prerequisites": ["cecum_identified"],
    "anatomical_targets": ["appendix"],
    "required_instruments": ["grasper"],
    "expected_action_duration_seconds": 30,
    "possible_outcomes": [
      {
        "id": "appendix_found",
        "probability_modifier": 1.0,
        "physiology_consequences": {"blood_loss": 0},
        "score_delta": 10,
        "next_phase": "phase_division"
      },
      {
        "id": "appendix_not_found",
        "probability_modifier": 0.2,
        "physiology_consequences": {"blood_loss": 5},
        "complication_triggers": ["misidentification"],
        "score_delta": -5,
        "next_phase": "phase_exposure"
      }
    ]
  },
  {
    "id": "meso_clamp_01",
    "phase": "phase_division",
    "title": "Clip Mesoappendix",
    "description": "Apply a vascular clip to the mesoappendix before transection.",
    "prerequisites": ["appendix_found"],
    "anatomical_targets": ["mesoappendix"],
    "required_instruments": ["clip_applier"],
    "expected_action_duration_seconds": 20,
    "possible_outcomes": [
      {
        "id": "clip_success",
        "probability_modifier": 1.0,
        "physiology_consequences": {"blood_loss": 0},
        "score_delta": 5,
        "next_phase": "phase_closure"
      },
      {
        "id": "clip_failure",
        "probability_modifier": 0.1,
        "physiology_consequences": {"blood_loss": 15},
        "complication_triggers": ["bleeding"],
        "score_delta": -10,
        "next_phase": "phase_division"
      }
    ]
  }
]
```
*Important fields*:
- `id` – globally unique across all procedures.
- `phase` – must match a `phase.id` from `phases.json`.
- `prerequisites` – list of **outcome ids** that must have occurred earlier in the graph.
- `possible_outcomes` – each outcome defines:
  - `probability_modifier` (multiplies the base success probability derived from the current stress profile).
  - `physiology_consequences` – deterministic changes to the world state (blood loss, oxygen debt, shock, etc.).
  - `complication_triggers` – optional list of complication identifiers that the engine will instantiate.
  - `next_phase` – ID of the phase to transition to after this outcome.
  - `score_delta` – numeric impact on the trainee’s score.

### 2.6 `complications.json`
```json
[
  {
    "id": "bleeding",
    "description": "Active arterial bleed",
    "trigger_conditions": {
      "blood_loss": {"gt": 30}
    },
    "physiology_effects": {"shock": true, "heart_rate": 20},
    "remediation_actions": ["apply_pressure", "use_cautery"]
  },
  {
    "id": "hypoxia",
    "description": "SpO₂ < 90%",
    "trigger_conditions": {"spO2": {"lt": 90}},
    "physiology_effects": {"oxygen_debt": 10},
    "remediation_actions": ["increase_fio2", "ventilate"]
  }
]
```
*Complications are evaluated each tick by the shared **ComplicationAgent**.  When a trigger condition becomes true, the complication is added to `active_complication` and presented to the UI as an urgent action list.*

### 2.7 `scoring.json`
```json
{
  "max_score": 100,
  "outcome_weights": {
    "perfect": 1.0,
    "minor_error": 0.7,
    "major_error": 0.3,
    "critical_failure": 0.0
  },
  "exit_criteria": {
    "completed_phases": ["phase_closure"],
    "minimum_score": 60
  }
}
```
*Defines global scoring for the procedure and the condition that marks the case as *complete* (used by the engine to set `snapshot.completed`).*

---

## 3. Loading Flow (Engine side)
1. **Session start** receives `procedure_id`. The `SimulationService` calls `registry.load_procedure(proc_id)`. 
2. `registry` reads `config.json`, validates the JSON schema, and merges any optional Python plugin under `procedures/plugins/<proc>.py`. 
3. The resulting dictionary is handed to the `ProceduralPhaseEngine`, which builds a **directed‑acyclic graph** of phases → cards → outcomes. 
4. When a tick occurs, the engine:
   - Checks for *pending* decision cards (current phase, all prerequisites satisfied). 
   - Emits those cards as `options` in the WebSocket payload. 
   - If the UI sends an `option_id`, the engine looks up the card, samples an outcome using the **probability_modifier** × current stress‑profile base probability, applies deterministic `physiology_consequences`, optionally triggers a complication, updates the score, and advances to `next_phase`. 
5. The engine continues ticking autonomously (physiology evolves) even when no decision is made, guaranteeing the patient’s state changes over time (e.g., rising HR when bleeding persists). 
6. Once `exit_criteria` from `scoring.json` are satisfied, the engine flags `completed = true` and closes the replay chain.

---

## 4. Plugin Hooks (Optional per‑procedure extensions)
A procedure may provide a **pure** Python module `procedures/plugins/<proc>.py` exposing any of the following callables (all receive immutable data and must return immutable data):
```python
# Example: procedures/plugins/appendectomy.py

def custom_decision_engine(state: dict, tick: int) -> List[dict]:
    """Return extra decision options that are not represented in cards.json.
    Useful for emergency rescue actions that depend on dynamic physiology.
    """
    # Example – if blood_loss > 50, add a "call for blood" option.
    if state.get("blood_loss", 0) > 50:
        return [{
            "id": "emergency_transfusion",
            "title": "Request blood transfusion",
            "description": "Activate massive transfusion protocol.",
            "required_instruments": [],
            "prerequisites": [],
            "expected_action_duration_seconds": 10,
            "possible_outcomes": [{"id": "transfusion_success", "probability_modifier": 1.0, "physiology_consequences": {"blood_loss": -30}, "score_delta": 5, "next_phase": "current"}]
        }]
    return []

def post_tick(state: dict, tick: int) -> dict:
    """Deterministic post‑tick adjustments (e.g., automatic antibiotic dosing)."""
    # Example – give prophylactic antibiotics 30 min after incision.
    if tick == 30:
        state = {**state, "antibiotics_given": True}
    return state
```
*If a plugin is missing, the engine simply ignores that hook.*

---

## 5. Adding a New Procedure (Author’s Checklist)
1. Create a folder `scrubin-core/scrubin/procedures/<new_proc>/`.
2. Add the required JSON files (`config.json`, `phases.json`, `anatomy.json`, `instruments.json`, `cards.json`, `complications.json`, `scoring.json`).
3. (Optional) Add `plugins/<new_proc>.py` for custom deterministic hooks.
4. Run the unit‑test suite – the registry will automatically validate the JSON schemas.  No engine code change is required.
5. The UI will automatically list the new procedure after the next fetch of `/procedures`.

---

## 6. Guarantees
- **Determinism:** All JSON is immutable; all plugin functions are required to be pure.  Given the same seed, stress profile, and decision sequence, the world state trajectory is identical, enabling **exact replay**.
- **Scalability:** Adding 100+ procedures only adds static files; the engine loads them lazily and caches them, giving O(1) per‑session overhead.
- **Extensibility:** Complex branching is expressed via `prerequisites` and `next_phase` in decision cards, supporting non‑linear operative workflows.
- **Scientific Fidelity:** Authors base each JSON on peer‑reviewed operative atlases; the engine enforces physiologic realism (e.g., blood loss automatically drives shock, oxygen debt, etc.).

---

## 7. Next Steps (Implementation Roadmap)
- Implement the **registry loader** to read the new folder layout and validate schemas.  
- Extend `SimulationService` to consume `cards.json` and build the directed graph.  
- Add optional plugin discovery (`importlib.import_module`).  
- Update the FastAPI `POST /session/start` endpoint to accept `procedure_id` and forward it to the service.  
- Refactor the UI to fetch `/procedures` and render decision cards directly from the WebSocket payload.  
- Write unit‑tests for schema validation, graph construction, and deterministic outcome sampling.

---

*End of document.*