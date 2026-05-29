"""Decision node model used by the deterministic procedural engine.

A ``DecisionNode`` captures the semantics of a single educational decision –
whether the choice is correct, how it changes the patient physiology, any
hidden side‑effects, downstream complications that may be triggered, and which
future decisions become unlocked.  This expanded definition supports the full
feature set required by Phase A decision nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Dict, Any, Tuple

from scrubin.models.types import VitalDelta, Vitals, ComplicationState

# ---------------------------------------------------------------------------
# Helper type aliases / simple wrappers
# ---------------------------------------------------------------------------

# ``PhysiologicDelta`` is just an alias for ``VitalDelta`` – the decision nodes
# use the more descriptive name.
PhysiologicDelta = VitalDelta

# ---------------------------------------------------------------------------
# Sub‑structures referenced by ``DecisionNode``
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EducationalFeedback:
    title: str = ""
    what_happened: str = ""
    why_it_matters: str = ""
    anatomical_reasoning: str = ""
    physiologic_reasoning: str = ""
    procedural_reasoning: str = ""
    future_risk_explanation: str = ""
    recovery_guidance: str = ""
    educational_tags: List[str] = field(default_factory=list)
    board_style_explanation: str = ""

@dataclass(frozen=True)
class OptionMutationRule:
    unlock_options: List[str] = field(default_factory=list)
    remove_options: List[str] = field(default_factory=list)
    priority_weight_changes: Dict[str, float] = field(default_factory=dict)
    emergency_overrides: List[str] = field(default_factory=list)
    hidden_until_instability: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class FailurePropagation:
    latent_failure_score: float = 0.0
    cumulative_risk_delta: float = 0.0
    instability_contribution: float = 0.0
    contamination_contribution: float = 0.0
    hemorrhage_contribution: float = 0.0
    cognitive_overload_contribution: float = 0.0
    delayed_decompensation_ticks: int = 0

@dataclass(frozen=True)
class ProcedureStateMutation:
    unlock_phases: List[str] = field(default_factory=list)
    block_phases: List[str] = field(default_factory=list)
    advance_phase: bool = False
    repeat_phase: bool = False
    force_branch: Any = None
    terminate_procedure: bool = False
    require_consult: Any = None

@dataclass(frozen=True)
class ResourceImpact:
    # Placeholder – add fields as needed for future extensions.
    impact: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ExecutionProfile:
    execution_type: str = "instant"
    duration_seconds: float = 0.0
    interruptible: bool = False
    requires_stability: bool = False
    requires_visualization: bool = False
    requires_anesthesia_depth: bool = False
    requires_assistant: bool = False

@dataclass(frozen=True)
class HiddenEffect:
    id: str = ""
    description: str = ""
    progression_rate: float = 0.0
    reveal_threshold: float = 0.0
    escalation_threshold: float = 0.0
    affected_systems: List[str] = field(default_factory=list)
    delayed_manifestations: List[str] = field(default_factory=list)
    reversible: bool = True
    requires_intervention: bool = False

# Placeholder for future complication triggers.
@dataclass(frozen=True)
class ComplicationTrigger:
    trigger_id: str = ""
    condition: Any = None

# ---------------------------------------------------------------------------
# Core DecisionNode definition – includes all fields used by the Phase A nodes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionNode:
    # Core identity / metadata
    id: str
    label: str = ""
    canonical_name: str = ""
    category: str = ""
    phase_id: str = ""
    phase_index: int = 0
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False
    deprecated: bool = False
    educational_importance: float = 0.0
    board_relevance: float = 0.0
    realism_weight: float = 1.0
    correctness: str = "correct"
    confidence_score: float = 0.0
    is_terminal_error: bool = False
    requires_confirmation: bool = False

    # Core effects
    physiologic_delta: PhysiologicDelta = field(default_factory=PhysiologicDelta)
    anatomical_impacts: List[Any] = field(default_factory=list)
    hidden_effects: List[HiddenEffect] = field(default_factory=list)
    complication_triggers: List[ComplicationTrigger] = field(default_factory=list)
    failure_propagation: FailurePropagation = field(default_factory=FailurePropagation)
    procedure_mutation: ProcedureStateMutation = field(default_factory=ProcedureStateMutation)
    option_mutation: OptionMutationRule = field(default_factory=OptionMutationRule)
    resource_impact: ResourceImpact = field(default_factory=ResourceImpact)
    execution_profile: ExecutionProfile = field(default_factory=ExecutionProfile)
    educational_feedback: EducationalFeedback = field(default_factory=EducationalFeedback)

    # Scoring fields
    score_delta: float = 0.0
    efficiency_score: float = 0.0
    safety_score: float = 0.0
    tissue_handling_score: float = 0.0
    contamination_score: float = 0.0
    hemodynamic_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------------
    # Execution – deterministic, side‑effect‑free.
    # ---------------------------------------------------------------------
    def execute(self, world: "WorldState", rng: "SimulationRNG") -> "DecisionResult":
        """Apply the decision to ``world`` and return a ``DecisionResult``.

        The method never mutates its inputs – it builds a new ``WorldState`` via
        the ``with_*`` helpers defined on that class.
        """
        # Lazy imports to avoid circular dependencies.
        from scrubin.world.state import WorldState, TimelineEvent
        from scrubin.engine.decision_result import DecisionResult
        from scrubin.engine.random import SimulationRNG

        # 1️⃣ Apply physiologic delta – additive to current vitals.
        delta = self.physiologic_delta
        cur = world.physiology.vitals
        new_vitals = Vitals(
            spo2=cur.spo2 + delta.spo2,
            heart_rate=cur.heart_rate + delta.heart_rate,
            bp_systolic=cur.bp_systolic + delta.bp_systolic,
            bp_diastolic=cur.bp_diastolic + delta.bp_diastolic,
            temperature=cur.temperature + delta.temperature,
        )
        new_physiology = world.physiology.with_vitals(new_vitals)

        # 2️⃣ Register hidden effects – simply appended.
        new_hidden = world.hidden_effects + tuple(self.hidden_effects)

        # 3️⃣ Update cognitive state – record the decision and expose new options.
        cognitive = world.cognitive.add_decision(self.id).set_available(self.option_mutation.unlock_options)

        # 4️⃣ Update scoring – additive deltas.
        scoring = world.scoring.with_delta(
            total_score=self.score_delta,
            efficiency=self.efficiency_score,
            safety=self.safety_score,
            tissue_handling=self.tissue_handling_score,
            contamination=self.contamination_score,
            hemodynamic=self.hemodynamic_score,
        )

        # 5️⃣ Append a timeline event for traceability.
        event = TimelineEvent(tick=world.tick, description=self.id)

        # 6️⃣ Assemble the new world state.
        new_world = (
            world
            .with_physiology(new_physiology)
            .with_hidden_effects(new_hidden)
            .with_cognitive(cognitive)
            .with_scoring(scoring)
            .append_timeline(event)
        )

        # 7️⃣ Package the result.
        result = DecisionResult(
            world=new_world,
            feedback=self.educational_feedback,
            events=[event],
            score_delta=self.score_delta,
            triggered_complications=[],  # TODO: derive from hidden effects / complication triggers
            unlocked_options=self.option_mutation.unlock_options,
        )
        return result

    # ---------------------------------------------------------------------
    # Serialisation helpers (unchanged from the original minimal version)
    # ---------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "DecisionNode":
        """Construct a ``DecisionNode`` from a mapping.

        This implementation is intentionally permissive – missing fields fall
        back to the defaults defined on the dataclass.
        """
        # Helper to coerce ``VitalDelta``‑like fields.
        def _as_delta(value: Any) -> VitalDelta:
            if isinstance(value, VitalDelta):
                return value
            if isinstance(value, dict):
                return VitalDelta.from_dict(value)
            return VitalDelta()

        # Convert nested structures where appropriate.
        def _as_feedback(d: dict) -> EducationalFeedback:
            if isinstance(d, EducationalFeedback):
                return d
            if not isinstance(d, dict):
                return EducationalFeedback()
            return EducationalFeedback(
                title=d.get("title", ""),
                what_happened=d.get("what_happened", ""),
                why_it_matters=d.get("why_it_matters", ""),
                anatomical_reasoning=d.get("anatomical_reasoning", ""),
                physiologic_reasoning=d.get("physiologic_reasoning", ""),
                procedural_reasoning=d.get("procedural_reasoning", ""),
                future_risk_explanation=d.get("future_risk_explanation", ""),
                recovery_guidance=d.get("recovery_guidance", ""),
                educational_tags=d.get("educational_tags", []),
                board_style_explanation=d.get("board_style_explanation", ""),
            )

        def _as_option_rule(d: dict) -> OptionMutationRule:
            if isinstance(d, OptionMutationRule):
                return d
            if not isinstance(d, dict):
                return OptionMutationRule()
            return OptionMutationRule(
                unlock_options=d.get("unlock_options", []),
                remove_options=d.get("remove_options", []),
                priority_weight_changes=d.get("priority_weight_changes", {}),
                emergency_overrides=d.get("emergency_overrides", []),
                hidden_until_instability=d.get("hidden_until_instability", []),
            )

        def _as_hidden_effects(lst: List[dict]) -> List[HiddenEffect]:
            out: List[HiddenEffect] = []
            for item in lst or []:
                if isinstance(item, HiddenEffect):
                    out.append(item)
                elif isinstance(item, dict):
                    out.append(HiddenEffect(
                        id=item.get("id", ""),
                        description=item.get("description", ""),
                        progression_rate=item.get("progression_rate", 0.0),
                        reveal_threshold=item.get("reveal_threshold", 0.0),
                        escalation_threshold=item.get("escalation_threshold", 0.0),
                        affected_systems=item.get("affected_systems", []),
                        delayed_manifestations=item.get("delayed_manifestations", []),
                        reversible=item.get("reversible", True),
                        requires_intervention=item.get("requires_intervention", False),
                    ))
            return out

        return cls(
            id=data.get("id", ""),
            label=data.get("label", ""),
            canonical_name=data.get("canonical_name", ""),
            category=data.get("category", ""),
            phase_id=data.get("phase_id", ""),
            phase_index=data.get("phase_index", 0),
            priority=data.get("priority", 0),
            tags=data.get("tags", []),
            aliases=data.get("aliases", []),
            hidden=data.get("hidden", False),
            deprecated=data.get("deprecated", False),
            educational_importance=data.get("educational_importance", 0.0),
            board_relevance=data.get("board_relevance", 0.0),
            realism_weight=data.get("realism_weight", 1.0),
            correctness=data.get("correctness", "correct"),
            confidence_score=data.get("confidence_score", 0.0),
            is_terminal_error=data.get("is_terminal_error", False),
            requires_confirmation=data.get("requires_confirmation", False),
            physiologic_delta=_as_delta(data.get("physiologic_delta", {})),
            anatomical_impacts=data.get("anatomical_impacts", []),
            hidden_effects=_as_hidden_effects(data.get("hidden_effects", [])),
            complication_triggers=[],  # Placeholder – extend as needed.
            failure_propagation=FailurePropagation(**data.get("failure_propagation", {})),
            procedure_mutation=ProcedureStateMutation(**data.get("procedure_mutation", {})),
            option_mutation=_as_option_rule(data.get("option_mutation", {})),
            resource_impact=ResourceImpact(**data.get("resource_impact", {})),
            execution_profile=ExecutionProfile(**data.get("execution_profile", {})),
            educational_feedback=_as_feedback(data.get("educational_feedback", {})),
            score_delta=data.get("score_delta", 0.0),
            efficiency_score=data.get("efficiency_score", 0.0),
            safety_score=data.get("safety_score", 0.0),
            tissue_handling_score=data.get("tissue_handling_score", 0.0),
            contamination_score=data.get("contamination_score", 0.0),
            hemodynamic_score=data.get("hemodynamic_score", 0.0),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict:
        """Serialise the node – mirrors the original minimal implementation."""
        return {
            "id": self.id,
            "correct": self.correct,
            "physiologic_effects": self.physiologic_delta.to_dict(),
            "hidden_effects": {he.id: he.to_dict() for he in self.hidden_effects},
            "future_complications": list(self.complication_triggers),
            "unlocks": list(self.unlocks),
        }
