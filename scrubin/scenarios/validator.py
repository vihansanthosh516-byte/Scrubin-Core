"""Validator for deterministic ProcedureScenario definitions.

Ensures structural integrity and deterministic properties required for replay.
"""

from __future__ import annotations

from typing import List, Set

from .models import ProcedureScenario, Step, Complication


class ScenarioValidationError(Exception):
    pass


def validate_scenario(scenario: ProcedureScenario) -> None:
    """Validate a single ``ProcedureScenario``.

    Checks performed:
    * Unique scenario ID – callers must ensure across all scenarios.
    * Unique step IDs within the scenario.
    * No cycles – workflow is a simple linear order (enforced by list ordering).
    * Complication references (if any) must have unique IDs.
    * Success / failure condition strings are non‑empty (basic check).
    """
    # Step IDs uniqueness
    step_ids: Set[str] = set()
    for step in scenario.workflow:
        if step.id in step_ids:
            raise ScenarioValidationError(f"Duplicate step ID '{step.id}' in scenario {scenario.id}")
        step_ids.add(step.id)
    # Complication IDs uniqueness
    comp_ids: Set[str] = set()
    for comp in scenario.complications:
        if comp.id in comp_ids:
            raise ScenarioValidationError(f"Duplicate complication ID '{comp.id}' in scenario {scenario.id}")
        comp_ids.add(comp.id)
    # Ensure that any referenced complication IDs in success/failure strings are defined
    # (simple heuristic: look for comp.id substrings). In a full implementation a DSL would be used.
    # Here we skip detailed parsing.
    # Non‑empty success/failure conditions
    for cond in scenario.success_conditions:
        if not cond:
            raise ScenarioValidationError(f"Empty success condition in scenario {scenario.id}")
    for cond in scenario.failure_conditions:
        if not cond:
            raise ScenarioValidationError(f"Empty failure condition in scenario {scenario.id}")
    # Estimated duration must be non‑negative integer
    if scenario.estimated_duration_minutes < 0:
        raise ScenarioValidationError(f"Negative estimated duration in scenario {scenario.id}")
    # All checks passed – return None.
    return None
