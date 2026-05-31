"""Deterministic Physiologic Evolution Engine.

This engine updates the immutable ``WorldState`` on each simulation tick. It
incorporates:

* organ‑system compensation and de‑compensation,
* deterministic complication escalation (via ``ComplicationEngine``),
* hidden‑effect progression and manifestation,
* time‑pressure effects, and
* timeline event emission.

All state transitions are pure – a new ``WorldState`` is returned and the
original is left untouched, guaranteeing replay safety.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Tuple

from scrubin.world.state import (
    WorldState,
    PhysiologicalState,
    ProcedureState,
    ComplicationWorldState,
    CognitiveState,
    ScoringState,
    ResourceState,
)
from scrubin.core.events import TimelineEvent
from scrubin.cognition.goal_management_engine import GoalManagementEngine
from scrubin.cognition.reflection_engine import ReflectionEngine
from scrubin.cognition.meta_learning_engine import MetaLearningEngine
from scrubin.cognition.pattern_extraction_engine import PatternExtractionEngine
from scrubin.cognition.belief_formation_engine import BeliefFormationEngine
from scrubin.cognition.belief_validation_engine import BeliefValidationEngine
from scrubin.cognition.knowledge_graph_engine import KnowledgeGraphEngine
from scrubin.cognition.arbitration_engine import CognitiveArbitrationEngine
from scrubin.engine.random import SimulationRNG
from scrubin.cognition.intent_synthesis_engine import IntentSynthesisEngine
from scrubin.models.types import ComplicationState, ComplicationSeverity
from scrubin.engine.decision_node import HiddenEffect
from scrubin.ontology.activation_engine import SemanticActivationEngine
from scrubin.ontology.prediction_engine import SemanticPredictionEngine
from scrubin.ontology.conflict_engine import ConflictEngine
from scrubin.ontology.attention_engine import AttentionEngine
from scrubin.cognition.overload_engine import OverloadEngine
from scrubin.ontology.executive_planner import ExecutivePlanner
from scrubin.ontology.intent_scheduler import IntentScheduler
from scrubin.ontology.recovery_engine import RecoveryEngine
from scrubin.ontology.strategic_engine import StrategicEngine
from scrubin.agents.runtime_engine import MultiAgentRuntimeEngine
from scrubin.engine.systems_biology_engine import SystemsBiologyEngine
from scrubin.execution.workflow_engine import WorkflowEngine
from scrubin.execution.maneuver_engine import ManeuverExecutionEngine
from scrubin.execution.instrument_engine import InstrumentInteractionEngine
from scrubin.execution.error_engine import TechnicalErrorEngine
from scrubin.execution.tissue_consequence_engine import TissueConsequenceEngine
from scrubin.biology.contamination_ecology import ContaminationEcologyEngine
from scrubin.execution.friction_engine import FrictionEngine
from scrubin.environment.equipment_runtime import EquipmentRuntimeEngine
from scrubin.adaptive.competency_engine import CompetencyEvolutionEngine
from scrubin.adaptive.difficulty_engine import AdaptiveDifficultyEngine
from scrubin.adaptive.tutoring_engine import TutoringEngine
from scrubin.adaptive.failure_anticipation import FailureAnticipationEngine
from scrubin.adaptive.curriculum_engine import CurriculumEngine
from scrubin.adaptive.analytics_engine import AnalyticsEngine

# ---------------------------------------------------------------------------
# Organ‑system state definitions (simplified for demonstration)
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CardiovascularState:
    map: float = 100.0  # mean arterial pressure
    heart_rate: float = 80.0
    compensation_active: bool = False
    reserve: float = 1.0  # abstract reserve for compensation
    failure_threshold: float = 50.0

    def with_map(self, new_map: float) -> "CardiovascularState":
        return replace(self, map=new_map)

    def with_heart_rate(self, new_hr: float) -> "CardiovascularState":
        return replace(self, heart_rate=new_hr)

    def with_compensation(self, active: bool, reserve: float) -> "CardiovascularState":
        return replace(self, compensation_active=active, reserve=reserve)


@dataclass(frozen=True)
class RespiratoryState:
    spo2: float = 98.0
    compensation_active: bool = False
    reserve: float = 1.0
    failure_threshold: float = 85.0

    def with_spo2(self, new_spo2: float) -> "RespiratoryState":
        return replace(self, spo2=new_spo2)

    def with_compensation(self, active: bool, reserve: float) -> "RespiratoryState":
        return replace(self, compensation_active=active, reserve=reserve)

# Additional organ states can be added similarly (perfusional, neurologic, renal, ...)


# ---------------------------------------------------------------------------
# Main Evolution Engine
# ---------------------------------------------------------------------------

class PhysiologicEvolutionEngine:
    """Deterministic engine that evolves the world physiologically each tick.

    The engine is deliberately pure – it never mutates its inputs.  All
    side‑effects (new complications, timeline events) are encoded in the returned
    ``WorldState``.
    """

    def __init__(self, rng: SimulationRNG):
        self.rng = rng
        # Simple deterministic mapping from complication id to progression delta
        self.complication_deltas: Dict[str, Dict[str, float]] = {
            "hemorrhage": {"map": -10.0},
            "sepsis": {"spo2": -5.0},
        }
        self.biology_engine = SystemsBiologyEngine(rng)
        self.agent_runtime_engine = MultiAgentRuntimeEngine(rng)
        self.strategic_engine = StrategicEngine(rng)
        self.activation_engine = SemanticActivationEngine(rng)
        self.prediction_engine = SemanticPredictionEngine(rng)
        self.conflict_engine = ConflictEngine(rng)
        self.attention_engine = AttentionEngine(rng)
        self.overload_engine = OverloadEngine(rng)
        self.intent_synthesis_engine = IntentSynthesisEngine(rng)
        self.planner = ExecutivePlanner(rng)
        self.intent_scheduler = IntentScheduler(rng)
        self.recovery_engine = RecoveryEngine(rng)
        self.workflow_engine = WorkflowEngine(rng)
        self.maneuver_engine = ManeuverExecutionEngine(rng)
        self.instrument_engine = InstrumentInteractionEngine(rng)
        self.error_engine = TechnicalErrorEngine(rng)
        self.competency_engine = CompetencyEvolutionEngine(rng)
        self.difficulty_engine = AdaptiveDifficultyEngine(rng)
        self.tutoring_engine = TutoringEngine(rng)
        self.failure_anticipation_engine = FailureAnticipationEngine(rng)
        self.curriculum_engine = CurriculumEngine(rng)
        self.analytics_engine = AnalyticsEngine(rng)
        self.goal_management_engine = GoalManagementEngine(rng)
        self.reflection_engine = ReflectionEngine(rng)
        self.meta_learning_engine = MetaLearningEngine(rng)
        self.pattern_extraction_engine = PatternExtractionEngine(rng)
        self.belief_formation_engine = BeliefFormationEngine(rng)
        self.belief_validation_engine = BeliefValidationEngine(rng)
        self.knowledge_graph_engine = KnowledgeGraphEngine(rng)
        self.arbitration_engine = CognitiveArbitrationEngine(rng)

    def _apply_complications(self, world: WorldState) -> WorldState:
        """Apply active complication effects to organ systems.

        Complication effects are defined in ``self.complication_deltas``.  The
        example mappings are intentionally simple but deterministic.
        """
        cardio = world.physiology.cardiovascular
        resp = world.physiology.respiratory
        for comp in world.complications.active:
            deltas = self.complication_deltas.get(comp.id, {})
            if "map" in deltas:
                new_map = max(0.0, cardio.map + deltas["map"])
                cardio = cardio.with_map(new_map)
            if "spo2" in deltas:
                new_spo2 = max(0.0, resp.spo2 + deltas["spo2"])
                resp = resp.with_spo2(new_spo2)
        return world.with_physiology(
            replace(world.physiology, cardiovascular=cardio, respiratory=resp)
        )

    def _compensate(self, world: WorldState) -> WorldState:
        """Apply deterministic compensation mechanisms.

        * Tachycardia compensates for low MAP.
        * Increased respiratory rate (simulated as higher ``spo2``) compensates for
          low oxygen delivery.
        Compensation consumes a reserve; when the reserve reaches 0 the
        mechanism fails and a ``compensation_failed`` event is emitted.
        """
        cardio = world.physiology.cardiovascular
        resp = world.physiology.respiratory
        events: List[TimelineEvent] = []

        # MAP compensation via tachycardia
        if cardio.map < 70.0 and cardio.reserve > 0.0:
            # Activate compensation if not already active
            if not cardio.compensation_active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_started:cardiovascular"))
            # Increase heart rate modestly
            new_hr = cardio.heart_rate + 5.0
            new_reserve = max(0.0, cardio.reserve - 0.1)
            active = new_reserve > 0.0
            cardio = cardio.with_heart_rate(new_hr).with_compensation(active, new_reserve)
            if not active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_failed:cardiovascular"))

        # SpO2 compensation via respiratory effort (placeholder)
        if resp.spo2 < 92.0 and resp.reserve > 0.0:
            if not resp.compensation_active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_started:respiratory"))
            # Slightly improve spo2
            new_spo2 = min(100.0, resp.spo2 + 2.0)
            new_reserve = max(0.0, resp.reserve - 0.1)
            active = new_reserve > 0.0
            resp = resp.with_spo2(new_spo2).with_compensation(active, new_reserve)
            if not active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_failed:respiratory"))
        # Apply any generated events to the timeline
        new_world = world.with_physiology(
            replace(world.physiology, cardiovascular=cardio, respiratory=resp)
        )
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world

    def _progress_hidden_effects(self, world: WorldState) -> WorldState:
        """Progress hidden effects and manifest them as complications when due.
        """
        new_hidden: List[HiddenEffect] = []
        new_complications = world.complications
        events: List[TimelineEvent] = []
        for he in world.hidden_effects:
            # Simple deterministic progression: advance a tick counter implicitly via world.tick.
            # When the current tick reaches the reveal threshold, manifest the effect.
            if world.tick >= he.reveal_threshold:
                # Manifest as a complication (use the hidden effect id as complication id).
                comp = ComplicationState(id=he.id, severity="moderate", onset_tick=world.tick)
                new_complications = new_complications.with_added(comp)
                events.append(TimelineEvent(tick=world.tick, description=f"occult_instability_detected:{he.id}"))
            else:
                new_hidden.append(he)
        # Preserve any hidden effects that have not yet manifested.
        new_world = world.with_hidden_effects(tuple(new_hidden)).with_complications(new_complications)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world

    def _apply_time_pressure(self, world: WorldState) -> WorldState:
        """Simple time‑pressure model – increase instability with prolonged ticks.

        If the tick count exceeds a hard‑coded threshold (e.g., 30), we add a low‑
        severity ``time_pressure`` complication.
        """
        if world.tick > 30:
            comp = ComplicationState(id="time_pressure", severity="mild", onset_tick=world.tick)
            new_comp = world.complications.with_added(comp)
            ev = TimelineEvent(tick=world.tick, description="time_pressure_active")
            return world.with_complications(new_comp).append_timeline(ev)
        return world

    def evolve(self, world: WorldState) -> WorldState:
        """Advance the world by one deterministic physiologic tick.

        The order of operations mirrors typical physiologic cascades:
        1. Apply active complication effects.
        2. Apply compensatory mechanisms.
        3. Progress hidden effects.
        4. Apply time‑pressure penalties.
        5. Increment the tick counter.
        """
        # 1️⃣ Complication impact
        world = self._apply_complications(world)
        # 2️⃣ Compensation
        world = self._compensate(world)
        # 3️⃣ Hidden effect progression
        world = self._progress_hidden_effects(world)
        # 4️⃣ Time pressure
        world = self._apply_time_pressure(world)
        # Fast‑path for trivial worlds (no anatomy, complications, hidden effects, intents, or tutoring interventions)
        if not world.anatomy.regions and not world.complications.active and not world.hidden_effects and not world.intent_graph.pending_intents() and not world.tutoring_state.active_interventions:
            # Skip heavy engine invocations – just advance the tick.
            return world.tick_forward()
        # 5️⃣ Biological subsystem evolution (deterministic)
        world = self.biology_engine.evolve(world)
        # 6️⃣ Strategic engines (placeholder)
        world = self.strategic_engine.process(world)
        # 7️⃣ Semantic activation engine
        world = self.activation_engine.evolve(world)
        # 8️⃣ Prediction engine
        world = self.prediction_engine.predict(world)
        # 9️⃣ Conflict engine
        world = self.conflict_engine.resolve(world)
        # 🔟 Attention engine
        world = self.attention_engine.evolve(world)
        # 11️⃣ Overload engine
        world = self.overload_engine.evolve(world)
        world = self.goal_management_engine.evolve(world)
        world = self.arbitration_engine.evolve(world)
        world = self.intent_synthesis_engine.evolve(world)
        # 12️⃣ Executive planner
        world = self.planner.plan(world)
        # 13️⃣ Intent scheduler
        world = self.intent_scheduler.schedule(world)
        # 14️⃣ Workflow engine
        world = self.workflow_engine.process(world)
        # 15️⃣ Maneuver execution
        world = self.maneuver_engine.execute(world)
        # 16️⃣ Instrument interaction
        world = self.instrument_engine.interact(world)
        # 17️⃣ Technical error propagation
        world = self.error_engine.propagate(world)
        # 18️⃣ Recovery engine
        # Adaptive stages
        world = self.competency_engine.evolve(world)
        world = self.difficulty_engine.adapt(world)
        world = self.tutoring_engine.coach(world)
        world = self.failure_anticipation_engine.analyze(world)
        world = self.curriculum_engine.evolve(world)
        world = self.analytics_engine.analyze(world)
        world = self.recovery_engine.recover(world)
        world = self.reflection_engine.evolve(world)
        world = self.meta_learning_engine.evolve(world)
        world = self.pattern_extraction_engine.evolve(world)
        world = self.belief_formation_engine.evolve(world)
        world = self.belief_validation_engine.evolve(world)
        world = self.knowledge_graph_engine.evolve(world)
        # 19️⃣ Multi‑agent runtime evolution (deterministic)
        world = self.agent_runtime_engine.evolve(world)
        # 20️⃣ Advance tick (deterministic)
        world = world.tick_forward()
        return world
