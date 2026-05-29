"""Procedural phase model for deterministic curriculum pathways.

The engine operates on JSON procedure definitions (e.g. ``scrubin/procedures/*.json``).
This module provides a lightweight, typed representation that can be constructed
directly from the JSON structure used by the existing ``procedure_registry``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any
from scrubin.world.state import WorldState
from .constraints import Constraint


@dataclass
class ProcedurePhase:
    """Represent a single phase of a surgical procedure.

    The model is now constraint‑driven: entry, completion and failure are
    expressed as declarative :class:`Constraint` objects that can be evaluated
    against a :class:`WorldState`.  This eliminates hard‑coded index checks and
    enables dynamic, context‑sensitive progression.

    Attributes
    ----------
    id: str
        Unique identifier for the phase (derived from the JSON name).
    title: str
        Human‑readable title of the phase.
    macro_phase: str
        High‑level grouping (e.g. ``"pre‑operative"``).
    sub_phase: str
        Sub‑group within the macro phase (e.g. ``"assessment"``).
    objectives: List[str]
        High‑level educational objectives for the phase.
    required_decisions: List[str]
        Decision identifiers that must be performed during the phase.
    entry_conditions: List[Constraint]
        Predicates that must be satisfied before the phase may be entered.
    completion_conditions: List[Constraint]
        Predicates that define successful completion of the phase.
    failure_conditions: List[Constraint]
        Predicates that trigger phase failure.
    instability_limits: List[Constraint]
        Bounds on physiological instability that, if exceeded, block progression.
    prohibited_complications: List[str]
        Complication IDs that must not be active for the phase to continue.
    required_exposures: List[str]
        Anatomical exposures that must be established (e.g. ``"appendix_visible"``).
    required_resources: List[str]
        Named resources that must be available (e.g. ``"blood_units"``).
    hidden_state_requirements: List[Constraint]
        Checks against hidden effects (e.g. presence of a latent infection).
    minimum_visualization_score: float
        Minimum score from a visualization assessment (e.g. SOFA, NEWS2) needed to progress.
    time_pressure_modifiers: Dict[str, float]
        Mapping of time‑based penalties that apply if the phase exceeds a duration.
    escalation_rules: List[Constraint]
        Conditions that trigger emergency escalation or rescue paths.
    """

    id: str
    title: str
    macro_phase: str = ""
    sub_phase: str = ""
    objectives: List[str] = field(default_factory=list)
    required_decisions: List[str] = field(default_factory=list)
    entry_conditions: List[Constraint] = field(default_factory=list)
    completion_conditions: List[Constraint] = field(default_factory=list)
    failure_conditions: List[Constraint] = field(default_factory=list)
    instability_limits: List[Constraint] = field(default_factory=list)
    prohibited_complications: List[str] = field(default_factory=list)
    required_exposures: List[str] = field(default_factory=list)
    required_resources: List[str] = field(default_factory=list)
    hidden_state_requirements: List[Constraint] = field(default_factory=list)
    minimum_visualization_score: float = 0.0
    time_pressure_modifiers: Dict[str, float] = field(default_factory=dict)
    escalation_rules: List[Constraint] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # ---------------------------------------------------------------------
    # Predicate evaluation helpers – these are thin wrappers around the
    # underlying ``Constraint`` objects.  They return ``True``/``False`` and do
    # not mutate the world.
    # ---------------------------------------------------------------------
    def can_enter(self, world: WorldState) -> bool:
        """Return ``True`` if **all** ``entry_conditions`` evaluate to ``True``.

        If a condition raises an exception, it is treated as a failure (``False``).
        """
        return all(c.evaluate(world) for c in self.entry_conditions)

    def can_complete(self, world: WorldState) -> bool:
        """Return ``True`` if the phase meets **all** completion criteria.

        This includes ``completion_conditions`` as well as any additional
        limits such as ``instability_limits`` and ``prohibited_complications``.
        """
        # Core completion predicates
        core = all(c.evaluate(world) for c in self.completion_conditions)
        # Instability limits – any failing limit blocks completion
        stable = all(c.evaluate(world) for c in self.instability_limits)
        # No prohibited complications should be active
        no_prohibited = all(comp not in [c.id for c in world.complications.active] for comp in self.prohibited_complications)
        # Required exposures and resources must be satisfied (simple presence checks)
        exposures_ok = all(getattr(world, exp, None) is not None for exp in self.required_exposures)
        resources_ok = all(res in dict(world.resources.resources) for res in self.required_resources)
        # Hidden state requirements
        hidden_ok = all(c.evaluate(world) for c in self.hidden_state_requirements)
        return core and stable and no_prohibited and exposures_ok and resources_ok and hidden_ok

    def should_fail(self, world: WorldState) -> bool:
        """Return ``True`` if any failure predicate is satisfied.

        Failure can also be triggered by exceeding instability limits or by the
        presence of a prohibited complication.
        """
        failure = any(c.evaluate(world) for c in self.failure_conditions)
        instability_failure = any(not c.evaluate(world) for c in self.instability_limits)
        prohibited = any(comp in [c.id for c in world.complications.active] for comp in self.prohibited_complications)
        return failure or instability_failure or prohibited

    @classmethod
    def from_dict(cls, data: dict) -> "ProcedurePhase":
        """Create a :class:`ProcedurePhase` from a procedure JSON dict.

        The legacy JSON uses keys ``name``, ``objective``, ``instructions``,
        ``success_criteria`` and ``risk_flags``.  This method maps the legacy
        keys onto the richer dataclass fields.
        """
        title = data.get("name") or data.get("title") or "Unnamed Phase"
        phase_id = data.get("id") or title.lower().replace(" ", "_")
        # ``objective`` is a single string; wrap it into a list for consistency.
        objectives = [data["objective"]] if "objective" in data else []
        required_decisions = data.get("instructions", [])
        advancement_rules = data.get("success_criteria", [])
        failure_conditions = data.get("risk_flags", [])
        return cls(
            id=phase_id,
            title=title,
            objectives=objectives,
            required_decisions=required_decisions,
            advancement_rules=advancement_rules,
            failure_conditions=failure_conditions,
        )

    def to_dict(self) -> dict:
        """Serialise the phase back to a plain ``dict``.
        Useful for debugging or persisting custom modifications.
        """
        return {
            "id": self.id,
            "title": self.title,
            "objectives": self.objectives,
            "required_decisions": self.required_decisions,
            "advancement_rules": self.advancement_rules,
            "failure_conditions": self.failure_conditions,
        }
