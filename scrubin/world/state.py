from __future__ import annotations

"""Immutable world state for the procedural cognition engine.

The design mirrors :class:`scrubin.models.types.SimulationState` but is fully
immutable (frozen dataclasses) and broken into fine‑grained sub‑objects that can
be updated via ``with_*`` helper methods.  All mutation returns a brand‑new
instance – no in‑place changes are ever performed.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple, List, Any

from scrubin.models.types import Vitals, VitalDelta, ComplicationState
from scrubin.cognition.state import CognitiveState
from scrubin.cognition.intentive_state import IntentiveCognitionState
from scrubin.core.events import TimelineEvent
from scrubin.agents.state import OperativeActor
from scrubin.ontology.active_graph import ActiveSemanticGraph
from scrubin.execution.state import TechnicalExecutionState
from scrubin.execution.skill_model import OperatorSkillProfile
from scrubin.adaptive.competency import OperatorCompetencyProfile
from scrubin.adaptive.difficulty_engine import DifficultyProfile
from scrubin.adaptive.tutoring_engine import TutoringState
from scrubin.adaptive.curriculum_engine import AdaptiveCurriculum
from scrubin.adaptive.analytics_engine import PerformanceAnalytics
from scrubin.cognition.procedural_memory import ProceduralMemory
from scrubin.environment.state import OperativeEnvironmentState
from scrubin.memory.consequence_memory import ConsequenceMemory
from scrubin.anatomy.state import AnatomicalState
from scrubin.biology.state import SystemsBiologyState
from scrubin.ontology.intent_graph import IntentGraph
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.overload_state import OverloadState
from scrubin.ontology.intent_schedule import IntentSchedule
from scrubin.ontology.memory_compression import EpisodicMemory
from scrubin.ontology.recovery_state import RecoveryState

# ---------------------------------------------------------------------------
# Sub‑state definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CardiovascularState:
    """Simplified cardiovascular subsystem.

    * ``map`` – mean arterial pressure.
    * ``heart_rate`` – beats per minute.
    * ``compensation_active`` – whether a compensatory response is engaged.
    * ``reserve`` – abstract reserve that depletes while compensating.
    * ``failure_threshold`` – MAP below which organ failure is flagged.
    """
    map: float = 100.0
    heart_rate: float = 80.0
    compensation_active: bool = False
    reserve: float = 1.0
    failure_threshold: float = 50.0

    def with_map(self, new_map: float) -> "CardiovascularState":
        return replace(self, map=new_map)

    def with_heart_rate(self, new_hr: float) -> "CardiovascularState":
        return replace(self, heart_rate=new_hr)

    def with_compensation(self, active: bool, reserve: float) -> "CardiovascularState":
        return replace(self, compensation_active=active, reserve=reserve)


@dataclass(frozen=True)
class RespiratoryState:
    """Simplified respiratory subsystem.

    * ``spo2`` – peripheral oxygen saturation.
    * ``compensation_active`` – whether increased effort is underway.
    * ``reserve`` – abstract reserve for compensation.
    * ``failure_threshold`` – SpO2 below which organ failure is considered.
    """
    spo2: float = 98.0
    compensation_active: bool = False
    reserve: float = 1.0
    failure_threshold: float = 85.0

    def with_spo2(self, new_spo2: float) -> "RespiratoryState":
        return replace(self, spo2=new_spo2)

    def with_compensation(self, active: bool, reserve: float) -> "RespiratoryState":
        return replace(self, compensation_active=active, reserve=reserve)


@dataclass(frozen=True)
class PhysiologicalState:
    """Patient physiological snapshot.

    ``vitals`` holds the basic vital signs. ``active_trajectories`` is kept as a
    tuple to preserve immutability.
    """
    vitals: Vitals = field(default_factory=Vitals)
    active_trajectories: Tuple[Any, ...] = field(default_factory=tuple)
    cardiovascular: CardiovascularState = field(default_factory=CardiovascularState)
    respiratory: RespiratoryState = field(default_factory=RespiratoryState)

    def with_vitals(self, vitals: Vitals) -> "PhysiologicalState":
        return replace(self, vitals=vitals)

    def with_active_trajectories(self, trajectories: Tuple[Any, ...]) -> "PhysiologicalState":
        return replace(self, active_trajectories=trajectories)

    def with_cardiovascular(self, cardio: CardiovascularState) -> "PhysiologicalState":
        return replace(self, cardiovascular=cardio)

    def with_respiratory(self, resp: RespiratoryState) -> "PhysiologicalState":
        return replace(self, respiratory=resp)


@dataclass(frozen=True)
class ProcedureState:
    """Tracks procedural progress.

    ``current_phase`` is a string identifier (e.g. ``"appendectomy_a1"``). ``completed``
    records all node IDs that have been executed.
    """
    current_phase: str = ""
    completed: Tuple[str, ...] = field(default_factory=tuple)

    def with_phase(self, phase: str) -> "ProcedureState":
        return replace(self, current_phase=phase)

    def add_completed(self, node_id: str) -> "ProcedureState":
        return replace(self, completed=self.completed + (node_id,))


@dataclass(frozen=True)
class ComplicationWorldState:
    """Immutable container for active complications.

    ``active`` is a tuple of :class:`scrubin.models.types.ComplicationState`.
    """
    active: Tuple[ComplicationState, ...] = field(default_factory=tuple)

    def with_added(self, comp: ComplicationState) -> "ComplicationWorldState":
        # Replace any existing instance with the same id/onset_tick
        filtered = tuple(c for c in self.active if not (c.id == comp.id and c.onset_tick == comp.onset_tick))
        return replace(self, active=filtered + (comp,))

    def without(self, comp_id: str) -> "ComplicationWorldState":
        return replace(self, active=tuple(c for c in self.active if c.id != comp_id))


# Hidden effects are defined in ``scrubin.engine.decision_node`` – we reuse that
# class here to keep a single source of truth.  Import is delayed to avoid a
# circular import at module load time.

def _hidden_effect_type():
    from scrubin.engine.decision_node import HiddenEffect
    return HiddenEffect


@dataclass(frozen=True)
class ResourceState:
    """Simple immutable mapping of resource names to integer amounts.

    Stored as a sorted tuple of ``(name, amount)`` pairs for deterministic
    ordering.
    """
    resources: Tuple[Tuple[str, int], ...] = field(default_factory=tuple)

    def with_updated(self, name: str, amount: int) -> "ResourceState":
        res = dict(self.resources)
        res[name] = amount
        # Ensure deterministic ordering by sorting the items.
        return replace(self, resources=tuple(sorted(res.items())))


@dataclass(frozen=True)
class CognitiveState:
    """Record of learner decisions and currently available options.

    ``decisions`` is an ordered tuple of node IDs that have been executed.
    ``available_options`` holds IDs that are currently selectable.
    """
    decisions: Tuple[str, ...] = field(default_factory=tuple)
    available_options: Tuple[str, ...] = field(default_factory=tuple)

    def add_decision(self, node_id: str) -> "CognitiveState":
        return replace(self, decisions=self.decisions + (node_id,))

    def set_available(self, options: List[str]) -> "CognitiveState":
        return replace(self, available_options=tuple(options))


@dataclass(frozen=True)
class ScoringState:
    """Aggregate scores for the current simulation.

    All fields default to ``0.0`` and ``with_delta`` applies incremental changes.
    """
    total_score: float = 0.0
    efficiency: float = 0.0
    safety: float = 0.0
    tissue_handling: float = 0.0
    contamination: float = 0.0
    hemodynamic: float = 0.0

    def with_delta(self, **kwargs: float) -> "ScoringState":
        # Update only known fields – ignore unknown keys.
        updates = {k: getattr(self, k) + kwargs.get(k, 0.0) for k in self.__dataclass_fields__}
        return replace(self, **updates)


# TimelineEvent moved to scrubin.core.events


# ---------------------------------------------------------------------------
# WorldState container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorldState:
    """Top‑level immutable simulation state.

    The class purposefully mirrors the older ``SimulationWorld`` but is fully
    immutable and split into sub‑objects that can be updated via ``with_*``
    helpers.
    """
    tick: int = 0
    seed: int = 0
    physiology: PhysiologicalState = field(default_factory=PhysiologicalState)
    procedure: ProcedureState = field(default_factory=ProcedureState)
    complications: ComplicationWorldState = field(default_factory=ComplicationWorldState)
    hidden_effects: Tuple[Any, ...] = field(default_factory=tuple)  # will hold ``HiddenEffect`` objects
    resources: ResourceState = field(default_factory=ResourceState)
    cognitive: CognitiveState = field(default_factory=CognitiveState)
    anatomy: AnatomicalState = field(default_factory=AnatomicalState)
    biology: SystemsBiologyState = field(default_factory=SystemsBiologyState)
    scoring: ScoringState = field(default_factory=ScoringState)
    timeline: Tuple[TimelineEvent, ...] = field(default_factory=tuple)
    active_semantic_graph: ActiveSemanticGraph = field(default_factory=ActiveSemanticGraph)
    intent_graph: IntentGraph = field(default_factory=IntentGraph)
    intentive_cognition_state: IntentiveCognitionState = field(default_factory=IntentiveCognitionState)
    attention_state: AttentionState = field(default_factory=AttentionState)
    intent_schedule: IntentSchedule = field(default_factory=IntentSchedule)
    overload_state: OverloadState = field(default_factory=OverloadState)
    episodic_memory: EpisodicMemory = field(default_factory=EpisodicMemory)
    recovery_state: RecoveryState = field(default_factory=RecoveryState)
    actors: Tuple["OperativeActor", ...] = field(default_factory=tuple)
    technical_execution_state: TechnicalExecutionState = field(default_factory=TechnicalExecutionState)
    operator_skill_profile: OperatorSkillProfile = field(default_factory=OperatorSkillProfile)
    operator_competency_profile: OperatorCompetencyProfile = field(default_factory=OperatorCompetencyProfile)
    difficulty_profile: DifficultyProfile = field(default_factory=DifficultyProfile)
    tutoring_state: TutoringState = field(default_factory=TutoringState)
    adaptive_curriculum: AdaptiveCurriculum = field(default_factory=AdaptiveCurriculum)
    performance_analytics: PerformanceAnalytics = field(default_factory=PerformanceAnalytics)

    # ---------------------------------------------------------------------
    # Helper methods – each returns a brand‑new ``WorldState``
    # ---------------------------------------------------------------------
    def with_physiology(self, physiology: PhysiologicalState) -> "WorldState":
        return replace(self, physiology=physiology)

    def with_procedure(self, procedure: ProcedureState) -> "WorldState":
        return replace(self, procedure=procedure)

    def with_complications(self, complications: ComplicationWorldState) -> "WorldState":
        return replace(self, complications=complications)

    def with_hidden_effects(self, hidden_effects: Tuple[Any, ...]) -> "WorldState":
        return replace(self, hidden_effects=hidden_effects)

    def with_resources(self, resources: ResourceState) -> "WorldState":
        return replace(self, resources=resources)

    def with_cognitive(self, cognitive: CognitiveState) -> "WorldState":
        return replace(self, cognitive=cognitive)

    def with_anatomy(self, anatomy: AnatomicalState) -> "WorldState":
        return replace(self, anatomy=anatomy)

    def with_biology(self, biology: SystemsBiologyState) -> "WorldState":
        return replace(self, biology=biology)

    def with_scoring(self, scoring: ScoringState) -> "WorldState":
        return replace(self, scoring=scoring)

    def with_actors(self, actors: Tuple[OperativeActor, ...]) -> "WorldState":
        return replace(self, actors=actors)

    def with_tick(self, tick: int) -> "WorldState":
        return replace(self, tick=tick)

    def with_intent_graph(self, intent_graph: IntentGraph) -> "WorldState":
        return replace(self, intent_graph=intent_graph)

    def with_intentive_cognition_state(self, intentive_cognition_state: IntentiveCognitionState) -> "WorldState":
        return replace(self, intentive_cognition_state=intentive_cognition_state)

    def with_attention_state(self, attention_state: AttentionState) -> "WorldState":
        return replace(self, attention_state=attention_state)

    def with_intent_schedule(self, intent_schedule: IntentSchedule) -> "WorldState":
        return replace(self, intent_schedule=intent_schedule)

    def with_overload_state(self, overload_state: OverloadState) -> "WorldState":
        return replace(self, overload_state=overload_state)

    def with_technical_execution_state(self, technical_execution_state: TechnicalExecutionState) -> "WorldState":
        return replace(self, technical_execution_state=technical_execution_state)

    def with_operator_skill_profile(self, operator_skill_profile: OperatorSkillProfile) -> "WorldState":
        return replace(self, operator_skill_profile=operator_skill_profile)

    def with_operator_competency_profile(self, operator_competency_profile: OperatorCompetencyProfile) -> "WorldState":
        return replace(self, operator_competency_profile=operator_competency_profile)

    def with_difficulty_profile(self, difficulty_profile: DifficultyProfile) -> "WorldState":
        return replace(self, difficulty_profile=difficulty_profile)

    def with_tutoring_state(self, tutoring_state: TutoringState) -> "WorldState":
        return replace(self, tutoring_state=tutoring_state)

    def with_adaptive_curriculum(self, adaptive_curriculum: AdaptiveCurriculum) -> "WorldState":
        return replace(self, adaptive_curriculum=adaptive_curriculum)

    def with_performance_analytics(self, performance_analytics: PerformanceAnalytics) -> "WorldState":
        return replace(self, performance_analytics=performance_analytics)

    def with_episodic_memory(self, episodic_memory: EpisodicMemory) -> "WorldState":
        return replace(self, episodic_memory=episodic_memory)

    def with_recovery_state(self, recovery_state: RecoveryState) -> "WorldState":
        return replace(self, recovery_state=recovery_state)

    def with_actor(self, actor: OperativeActor) -> "WorldState":
        """Replace an actor with the same role, preserving deterministic ordering."""
        filtered = tuple(a for a in self.actors if a.role != actor.role)
        # Insert the updated actor at the end to keep deterministic order (role order is stable).
        return replace(self, actors=filtered + (actor,))

    def append_timeline(self, event: TimelineEvent) -> "WorldState":
        return replace(self, timeline=self.timeline + (event,))

    # ---------------------------------------------------------------------
    # Convenience shortcuts used by the engine
    # ---------------------------------------------------------------------
    def tick_forward(self) -> "WorldState":
        """Advance the tick counter by one.

        Returns a new ``WorldState`` with ``tick`` incremented.
        """
        return self.with_tick(self.tick + 1)
