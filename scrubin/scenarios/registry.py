"""Scenario registry – deterministic collection of surgical procedure scenarios.

The registry holds an immutable mapping of scenario ``id`` → ``ProcedureScenario``.
It provides deterministic ordering, validation, and a combined hash for the
entire library.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .models import (
    ProcedureScenario,
    PatientInfo,
    OperativeContext,
    Resources,
    Step,
    Complication,
)
from .validator import validate_scenario, ScenarioValidationError

# ---------------------------------------------------------------------------
# Helper to construct minimal yet valid scenarios
# ---------------------------------------------------------------------------

def _simple_scenario(
    sid: str,
    name: str,
    specialty: str,
    difficulty: str,
    description: str,
    steps: List[str],
) -> ProcedureScenario:
    """Factory for a minimal deterministic scenario.

    * ``steps`` – Ordered list of step IDs (strings).  Descriptions are empty.
    """
    workflow = tuple(Step(id=s, description="") for s in steps)
    patient = PatientInfo(
        age=30,
        sex="M",
        bmi=25.0,
        diagnosis="",
        comorbidities=(),
        allergies=(),
        baseline_vitals={},
    )
    operative_context = OperativeContext(
        or_setup="standard",
        positioning="supine",
        anatomy_variant="normal",
        pathology_severity="moderate",
    )
    resources = Resources(
        instruments=("scalpel", "forceps"),
        staff=("surgeon", "nurse"),
        medications=(),
        implants=(),
        equipment=(),
    )
    return ProcedureScenario(
        id=sid,
        display_name=name,
        specialty=specialty,
        difficulty=difficulty,
        description=description,
        patient=patient,
        operative_context=operative_context,
        resources=resources,
        workflow=workflow,
        complications=(),
        success_conditions=("completed",),
        failure_conditions=("critical_error",),
        teaching_objectives=(),
        estimated_duration_minutes=60,
        educational={},
    )

# ---------------------------------------------------------------------------
# Define all required scenarios (minimal placeholder definitions)
# ---------------------------------------------------------------------------

_SCENARIOS_LIST: List[ProcedureScenario] = [
    _simple_scenario(
        sid="lap_appendectomy",
        name="Laparoscopic Appendectomy",
        specialty="General Surgery",
        difficulty="moderate",
        description="Removal of the appendix via laparoscopy.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "divide_structure",
            "remove_specimen",
            "inspect",
            "irrigate",
            "close",
        ],
    ),
    _simple_scenario(
        sid="lap_cholecystectomy",
        name="Laparoscopic Cholecystectomy",
        specialty="General Surgery",
        difficulty="moderate",
        description="Removal of the gallbladder via laparoscopy.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "divide_structure",
            "remove_specimen",
            "inspect",
            "irrigate",
            "close",
        ],
    ),
    _simple_scenario(
        sid="right_hemicolectomy",
        name="Right Hemicolectomy",
        specialty="Colorectal Surgery",
        difficulty="hard",
        description="Resection of the right colon.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "divide_structure",
            "ligate",
            "remove_specimen",
            "inspect",
            "irrigate",
            "close",
        ],
    ),
    _simple_scenario(
        sid="left_hemicolectomy",
        name="Left Hemicolectomy",
        specialty="Colorectal Surgery",
        difficulty="hard",
        description="Resection of the left colon.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "divide_structure",
            "ligate",
            "remove_specimen",
            "inspect",
            "irrigate",
            "close",
        ],
    ),
    _simple_scenario(
        sid="inguinal_hernia_repair",
        name="Inguinal Hernia Repair",
        specialty="General Surgery",
        difficulty="easy",
        description="Repair of inguinal hernia.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "ligate",
            "close",
        ],
    ),
    _simple_scenario(
        sid="thyroidectomy",
        name="Thyroidectomy",
        specialty="Endocrine Surgery",
        difficulty="moderate",
        description="Removal of thyroid gland.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "divide_structure",
            "remove_specimen",
            "inspect",
            "close",
        ],
    ),
    _simple_scenario(
        sid="mastectomy",
        name="Mastectomy",
        specialty="Surgical Oncology",
        difficulty="moderate",
        description="Removal of breast tissue.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "divide_structure",
            "remove_specimen",
            "inspect",
            "close",
        ],
    ),
    _simple_scenario(
        sid="cesarean_section",
        name="Cesarean Section",
        specialty="Obstetrics",
        difficulty="moderate",
        description="Delivery of a baby via abdominal incision.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "incise",
            "deliver_fetus",
            "close",
        ],
    ),
    _simple_scenario(
        sid="trauma_laparotomy",
        name="Trauma Laparotomy",
        specialty="Trauma Surgery",
        difficulty="hard",
        description="Emergency abdominal exploration.",
        steps=[
            "establish_access",
            "identify_target",
            "expose_structure",
            "control_bleeding",
            "damage_control",
            "close",
        ],
    ),
    _simple_scenario(
        sid="bronchoscopy",
        name="Bronchoscopy",
        specialty="Pulmonology",
        difficulty="easy",
        description="Endoscopic inspection of the airways.",
        steps=["establish_access", "identify_target", "inspect", "close"],
    ),
    _simple_scenario(
        sid="upper_endoscopy",
        name="Upper Endoscopy",
        specialty="Gastroenterology",
        difficulty="easy",
        description="Endoscopic inspection of upper GI tract.",
        steps=["establish_access", "identify_target", "inspect", "close"],
    ),
    _simple_scenario(
        sid="colonoscopy",
        name="Colonoscopy",
        specialty="Gastroenterology",
        difficulty="easy",
        description="Endoscopic inspection of colon.",
        steps=["establish_access", "identify_target", "inspect", "close"],
    ),
    _simple_scenario(
        sid="central_venous_line",
        name="Central Venous Line Placement",
        specialty="Critical Care",
        difficulty="moderate",
        description="Insertion of a central venous catheter.",
        steps=["establish_access", "identify_target", "insert_catheter", "secure", "close"],
    ),
    _simple_scenario(
        sid="chest_tube_placement",
        name="Chest Tube Placement",
        specialty="Thoracic Surgery",
        difficulty="moderate",
        description="Insertion of a chest tube for pleural drainage.",
        steps=["establish_access", "identify_target", "incise", "insert_tube", "secure", "close"],
    ),
    _simple_scenario(
        sid="tracheostomy",
        name="Tracheostomy",
        specialty="ENT",
        difficulty="moderate",
        description="Creation of a tracheal opening.",
        steps=["establish_access", "identify_target", "incise", "insert_tube", "secure", "close"],
    ),
]

# Verify uniqueness of scenario IDs at import time.
_ID_SET = {s.id for s in _SCENARIOS_LIST}
if len(_ID_SET) != len(_SCENARIOS_LIST):
    raise ValueError("Duplicate scenario IDs detected in the registry")

# Build deterministic mapping (sorted by ID).
_SCENARIO_MAP: Dict[str, ProcedureScenario] = {s.id: s for s in sorted(_SCENARIOS_LIST, key=lambda x: x.id)}


class ScenarioRegistry:
    """Deterministic registry for surgical procedure scenarios.

    Provides ordered access, validation, and combined deterministic hash.
    """

    def __init__(self) -> None:
        # Perform validation once at construction.
        for scenario in _SCENARIOS_LIST:
            validate_scenario(scenario)
        self._scenarios = _SCENARIO_MAP

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------
    def list(self) -> List[ProcedureScenario]:
        """Return a deterministic list of all scenarios ordered by ID."""
        return [self._scenarios[sid] for sid in sorted(self._scenarios)]

    def get(self, scenario_id: str) -> ProcedureScenario:
        """Retrieve a scenario by its unique ID.

        Raises ``KeyError`` if the ID is unknown.
        """
        return self._scenarios[scenario_id]

    def deterministic_hash(self) -> str:
        """Return a combined deterministic hash for the entire scenario library.

        The hash is calculated from the concatenated deterministic hashes of each
        scenario in sorted order.
        """
        import hashlib
        concatenated = "|".join(self._scenarios[sid].deterministic_hash() for sid in sorted(self._scenarios))
        return hashlib.sha256(concatenated.encode()).hexdigest()

    def validate(self) -> None:
        """Validate the entire registry – raises ``ScenarioValidationError`` on failure."""
        for scenario in self._scenarios.values():
            validate_scenario(scenario)
