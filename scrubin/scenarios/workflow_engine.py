"""Deterministic workflow engine for ProcedureScenario execution.

The engine tracks immutable ``WorkflowState`` and produces deterministic events
that can be fed into the existing episode logging system.  All state updates
use ``dataclasses.replace`` to preserve immutability.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Tuple, List, Dict, Set, Optional

from .models import ProcedureScenario, Step, Complication, Resources, PatientInfo
from .physiology_engine import PhysiologyEngine, PhysiologyState
from scrubin.complications.engine import ComplicationEngine
from scrubin.anatomy.graph import AnatomyGraph
from scrubin.anatomy.interaction_engine import InteractionEngine
from .team_engine import TeamTaskEngine, TeamState

# ---------------------------------------------------------------------------
# Workflow state – immutable snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class WorkflowState:
    """Immutable representation of the current workflow execution.

    * current_step – ID of the step currently being executed (or ``None`` if
      idle).
    * completed_steps – Tuple of step IDs that have been successfully completed.
    * blocked_steps – Tuple of step IDs that are currently blocked by unmet
      prerequisites.
    * skipped_steps – Tuple of step IDs that were intentionally skipped (not used
      in the minimal engine but reserved for future extensions).
    * failed_steps – Tuple of step IDs that failed to execute (e.g., missing
      resources).
    * active_complications – Tuple of complication IDs that are currently active.
    """
    current_step: Optional[str]
    completed_steps: Tuple[str, ...]
    blocked_steps: Tuple[str, ...]
    skipped_steps: Tuple[str, ...]
    failed_steps: Tuple[str, ...]
    active_complications: Tuple[str, ...]
    deterministic_id: str = ""

    def __post_init__(self) -> None:
        # Compute a deterministic identifier for the state (useful for replay).
        combined = "|".join(
            [self.current_step or ""]
            + list(self.completed_steps)
            + list(self.blocked_steps)
            + list(self.skipped_steps)
            + list(self.failed_steps)
            + list(self.active_complications)
        )
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

# ---------------------------------------------------------------------------
# Engine implementation
# ---------------------------------------------------------------------------

class ScenarioWorkflowEngine:
    """Deterministic executor for a ``ProcedureScenario``.

    The engine is procedure‑agnostic – it interprets the scenario data to drive
    execution.  All state transitions are immutable; callers receive a new
    ``WorkflowState`` on each call.
    """

    def __init__(self, scenario: ProcedureScenario):
        self.scenario = scenario
        # Initial empty state – no current step, nothing completed.
        self.state = WorkflowState(
            current_step=None,
            completed_steps=(),
            blocked_steps=(),
            skipped_steps=(),
            failed_steps=(),
            active_complications=(),
        )
        # Initialise deterministic physiology and complication engines.
        self.physiology_engine = PhysiologyEngine(self.scenario.baseline_physiology)
        self.physiology_state = self.physiology_engine.initial_state()
        self.complication_engine = ComplicationEngine(self.scenario.complications)
        # Initialise deterministic OR team engine.
        self.team_engine = TeamTaskEngine(self.scenario.team_roles, tuple(self.scenario.resources.instruments))
        self.team_state = self.team_engine.initial_state()
        # Initialise deterministic anatomy interaction engine.
        self.anatomy_engine = InteractionEngine(AnatomyGraph(self.scenario.anatomy_structures))
        # Track the most recent successfully completed step for per‑step physiology modifiers.
        self.last_completed_step: Optional[str] = None

        # -------------------------------------------------------------------
    # Public query helpers
    # -------------------------------------------------------------------
    def current_step(self) -> Optional[str]:
        return self.state.current_step

    def completed_steps(self) -> Tuple[str, ...]:
        return self.state.completed_steps

    def blocked_steps(self) -> Tuple[str, ...]:
        return self.state.blocked_steps

    def next_available_steps(self) -> Tuple[str, ...]:
        """Return the next step ID that is executable given the current state.

        Steps are considered in workflow order; the first step that satisfies all
        prerequisite and resource checks is returned as a singleton tuple.  This
        deterministic ordering matches the test expectations for sequential
        execution.
        """
        for step in self.scenario.workflow:
            sid = step.id
            if sid in self.state.completed_steps or sid in self.state.failed_steps or sid in self.state.skipped_steps:
                continue
            if not self._prerequisites_met(step):
                continue
            if not self._resources_available(step):
                continue
            return (sid,)
        return ()

    # -------------------------------------------------------------------
    # Core execution method
    # -------------------------------------------------------------------
    def execute_step(self, step_id: str) -> Tuple[WorkflowState, List[Dict]]:
        """Attempt to execute ``step_id``.

        Returns a tuple ``(new_state, events)`` where ``events`` is a list of
        deterministic event dictionaries describing what happened.
        """
        # Locate the step definition.
        step = next((s for s in self.scenario.workflow if s.id == step_id), None)
        if step is None:
            # Unknown step – produce deterministic failure event.
            ev = {"type": "StepFailed", "step": step_id, "reason": "unknown_step"}
            new_state = replace(self.state, failed_steps=self.state.failed_steps + (step_id,))
            return new_state, [ev]
        # Check prerequisites.
        if not self._prerequisites_met(step):
            ev = {"type": "StepBlocked", "step": step_id, "reason": "prerequisites_unmet"}
            new_state = replace(self.state, blocked_steps=self.state.blocked_steps + (step_id,))
            return new_state, [ev]
        # Check resource availability.
        if not self._resources_available(step):
            ev = {"type": "StepFailed", "step": step_id, "reason": "resources_unavailable"}
            new_state = replace(self.state, failed_steps=self.state.failed_steps + (step_id,))
            return new_state, [ev]
        # All good – mark completed.
        events: List[Dict] = [{"type": "StepCompleted", "step": step_id}]
        new_completed = self.state.completed_steps + (step_id,)
        # Update blocked steps – re‑evaluate any previously blocked steps.
        new_blocked = tuple(s for s in self.state.blocked_steps if s != step_id)
        new_state = replace(self.state, current_step=None, completed_steps=new_completed, blocked_steps=new_blocked)
        # Process team tasks and instrument handling.
        self.team_state, team_events = self.team_engine.process_step(step, self.team_state)
        events.extend(team_events)
        # Evaluate any complications that trigger on this step via the deterministic engine.
        comp_events, active_ids = self.complication_engine.update(new_state, ())
        events.extend(comp_events)
        # Update the workflow state with the new active complication list.
        new_state = replace(new_state, active_complications=active_ids)
        # Anatomy interaction based on step naming convention (e.g., "cut_vessel1").
        interaction, target = self._parse_anatomy_interaction(step_id)
        if interaction and target:
            instrument = step.required_instruments[0] if step.required_instruments else ''
            self.anatomy_engine, anatomy_events, phys_delta = self.anatomy_engine.apply_interaction(interaction, target, instrument)
            events.extend(anatomy_events)
            # Apply physiology deltas derived from anatomy changes.
            if phys_delta:
                self.physiology_state, phys_events = self.physiology_engine.update(
                    self.physiology_state,
                    new_state.active_complications,
                    phys_delta,
                )
                events.extend(phys_events)
        # Record the most recent successful step for physiology modifiers.
        self.last_completed_step = step_id
        return new_state, events

    # -------------------------------------------------------------------
    # Helper – prerequisites checking
    # -------------------------------------------------------------------
    def _prerequisites_met(self, step: Step) -> bool:
        # ``requires_step_completed`` corresponds to ``prerequisite_steps``.
        return all(prereq in self.state.completed_steps for prereq in step.prerequisite_steps)

    # -------------------------------------------------------------------
    # Helper – resource availability
    # -------------------------------------------------------------------
    def _resources_available(self, step: Step) -> bool:
        # Verify required instruments, medications, implants, equipment against scenario resources.
        r = self.scenario.resources
        def contains_required(req: Tuple[str, ...], available: Tuple[str, ...]) -> bool:
            return all(item in available for item in req)
        if not contains_required(step.required_instruments, r.instruments):
            return False
        if not contains_required(step.required_medications, r.medications):
            return False
        if not contains_required(step.required_implants, r.implants):
            return False
        if not contains_required(step.required_equipment, r.equipment):
            return False
        return True

    # -------------------------------------------------------------------
    # Helper – complication evaluation
    # -------------------------------------------------------------------
    def _evaluate_complications(self, step_id: str, state: WorkflowState) -> Tuple[List[Dict], WorkflowState]:
        """Check for complications that trigger on the given step.

        Returns a list of deterministic events and the possibly updated state.
        """
        events: List[Dict] = []
        new_active = list(state.active_complications)
        for comp in self.scenario.complications:
            # Simple deterministic trigger: if the step ID appears in the trigger string.
            # In a full implementation a DSL would be parsed; here we use substring.
            if comp.id not in state.active_complications and comp.trigger and comp.trigger in step_id:
                # Trigger the complication.
                events.append({"type": "ComplicationTriggered", "complication": comp.id, "step": step_id})
                new_active.append(comp.id)
        # Resolve complications whose resolution condition is met – using similar simple check.
        resolved: List[str] = []
        for comp_id in new_active:
            comp = next((c for c in self.scenario.complications if c.id == comp_id), None)
            if comp and comp.resolution and comp.resolution in step_id:
                events.append({"type": "ComplicationResolved", "complication": comp.id, "step": step_id})
                resolved.append(comp_id)
        # Update active list.
        for rid in resolved:
            new_active.remove(rid)
        new_state = replace(state, active_complications=tuple(new_active))
        return events, new_state

    def _parse_anatomy_interaction(self, step_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse step identifier into (interaction, target_structure_id).

        Supported actions are: cut, retract, grasp, dissect, cauterize, staple,
        clip, suction, irrigate, divide.  If the step does not match the pattern,
        returns (None, None).
        """
        actions = (
            "cut",
            "retract",
            "grasp",
            "dissect",
            "cauterize",
            "staple",
            "clip",
            "suction",
            "irrigate",
            "divide",
        )
        for act in actions:
            prefix = f"{act}_"
            if step_id.startswith(prefix):
                return act, step_id[len(prefix) :]
        return None, None

    # -------------------------------------------------------------------
    # Victory / failure evaluation
    # -------------------------------------------------------------------
    def evaluate_outcome(self) -> Tuple[bool, List[str]]:
        """Return ``(success, messages)`` based on scenario success/failure conditions.

        The evaluation uses deterministic checks against the current workflow state and
        active complications.
        """
        messages: List[str] = []
        success = True
        # Helper for condition strings – a minimal parser interpreting simple
        # expressions of the form ``step_completed(step_id)`` or
        # ``complication_resolved(comp_id)``.
        def eval_condition(cond: str) -> bool:
            if cond.startswith("step_completed("):
                sid = cond[len("step_completed("):-1]
                return sid in self.state.completed_steps
            if cond.startswith("complication_resolved("):
                cid = cond[len("complication_resolved("):-1]
                return cid not in self.state.active_complications
            if cond == "patient_alive":
                # Placeholder – assume patient alive if no critical complication active.
                return len(self.state.active_complications) == 0
            if cond == "patient_stable":
                # Placeholder – same as alive for now.
                return len(self.state.active_complications) == 0
            return False
        # Evaluate success conditions.
        for cond in self.scenario.success_conditions:
            if not eval_condition(cond):
                success = False
                messages.append(f"Success condition not met: {cond}")
        # Evaluate failure conditions – any true failure condition forces failure.
        for cond in self.scenario.failure_conditions:
            if eval_condition(cond):
                success = False
                messages.append(f"Failure condition triggered: {cond}")
        return success, messages
