import uuid
from scrubin.compiler.execution_compiler import compile_execution_plan
from typing import Any

from scrubin.core.bus import EventBus
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.engine.random import SimulationRNG
from scrubin.core.ledger import EventLedger
from scrubin.core.config import ConfigLayer
from scrubin.execution.authority import ActionAuthority
from scrubin.models.intents import ActionIntent
from scrubin.events.action_helper import create_action_event
from scrubin.patient.profile import PatientProfile, STANDARD_PATIENT
from scrubin.complications.registry import ComplicationRegistry
from scrubin.world.model import SimulationWorld
from scrubin.contracts.validator import InvariantValidator
from scrubin.replay.snapshots import SnapshotEngine
from scrubin.audit.transitions import TransitionAuditor
from scrubin.perf.profiler import TickProfiler
from scrubin.perf.budgets import PerformanceBudgets
from scrubin.perf.metrics import PerformanceMetrics, TickMetrics
from scrubin.events.event_queue import EventQueue
from scrubin.cognition.memory_store import MemoryStore
from scrubin.cognition.fact_store import FactStore
from scrubin.cognition.belief_store import BeliefStore
from scrubin.cognition.reflection_store import ReflectionStore
from scrubin.cognition.reflection_engine import update_reflections_from_beliefs
from scrubin.cognition.belief_engine import update_beliefs_from_facts
from scrubin.cognition.memory_encoder import encode_events_to_episode
from scrubin.events import event_types
from scrubin.cognition.graph_store import GraphStore
from scrubin.cognition.graph_builder import update_graph
from scrubin.cognition.meta_store import MetaStore
from scrubin.cognition.meta_pattern_engine import update_meta_patterns
from scrubin.cognition.cognitive_pipeline import run_cognitive_pipeline
from scrubin.planner.plan_store import PlanStore
from scrubin.planner.long_horizon_planner import LongHorizonPlanner
from scrubin.events.event import SurgicalEvent
from scrubin.cognition.counterfactual import CounterfactualResult
from scrubin.cognition.counterfactual_store import CounterfactualStore
from scrubin.cognition.counterfactual_engine import run_counterfactual as _run_counterfactual
from scrubin.cognition.counterfactual import CounterfactualScenario
from scrubin.cognition.executive_goal import ExecutiveGoal
from scrubin.cognition.executive_store import ExecutiveStore
from scrubin.cognition.executive_engine import update_executive
from scrubin.cognition.priority_engine import compute_priority
from scrubin.cognition.executive_scheduler import schedule_goals
from scrubin.cognition.executive_monitor import monitor_goals
from scrubin.cognition.strategy_selection_store import StrategySelectionStore
from scrubin.cognition.strategy_selection_engine import update_strategy_selection
from scrubin.cognition.executive_evaluation_store import ExecutiveEvaluationStore
from scrubin.cognition.executive_evaluation_engine import update_executive_evaluations
from scrubin.cognition.policy_refinement import run_policy_refinement
from scrubin.cognition.bias_plan_store import BiasPlanStore
from scrubin.cognition.bias_planner_engine import update_bias_plan_candidates
from scrubin.cognition.executive_ranking import compute_executive_ranking
from scrubin.cognition.strategy_store import StrategyStore
from scrubin.cognition.policy_store import PolicyStore
from scrubin.cognition.policy_optimization_engine import update_policy_profiles
from scrubin.cognition.strategy_bias_engine import generate_strategy_bias
from scrubin.cognition.strategy_engine import update_strategies
from scrubin.cognition.executive_feedback_store import ExecutiveFeedbackStore
from scrubin.cognition.executive_feedback_engine import update_executive_feedback
from scrubin.cognition.executive_adaptation import generate_adaptation_signals
from scrubin.cognition.adaptation_store import AdaptationStore
from scrubin.cognition.adaptation_engine import update_adaptation_profiles
from scrubin.cognition.adaptation_bias_engine import generate_adaptation_biases
from scrubin.cognition.executive_optimization_store import ExecutiveOptimizationStore
from scrubin.cognition.executive_optimization_engine import update_executive_optimizations
from scrubin.cognition.executive_self_improvement_engine import generate_self_improvement_signals
from scrubin.cognition.executive_policy_engine import update_executive_policy
from scrubin.cognition.executive_policy_store import ExecutivePolicyStore
from scrubin.cognition.predictive_store import PredictiveStore

from scrubin.engine.physiology_events import generate_physiology_events
from scrubin.decision.consequence_engine import _recalculate_derived_metrics
from scrubin.engine.complication_events import generate_complication_events


from scrubin.control_plane.analysis.equilibrium import EquilibriumAnalyzer
from scrubin.control_plane.analysis.attractor import AttractorClassifier
from scrubin.control_plane.control.adversarial_controller import AdversarialController, ControlSignal


class Orchestrator:
    def __init__(self, seed=0, config: ConfigLayer = None, active_profile: str = "default",
                 decision_engine=None, decision_validator=None,
                 decision_executor=None, patient_profile: PatientProfile | None = None,
                 mode: str = "autonomous",
                 invariant_validator: InvariantValidator | None = None,
                 snapshot_interval: int = 50,
                 scenario_config: Any = None):
        self.seed = seed
        self.tick_count = 0
        self.ledger = EventLedger()
        self.bus = EventBus(ledger=self.ledger)
        self.active_profile = active_profile
        self.config = config or ConfigLayer(active_profile=active_profile)
        self.decision_engine = decision_engine
        self.decision_validator = decision_validator
        self.decision_executor = decision_executor
        self.patient_profile = patient_profile or STANDARD_PATIENT
        self.mode = mode
        self.authority = ActionAuthority(
            bus=self.bus,
            ledger=self.ledger,
            state=self,
        )
        self.bus.set_authority_token(self.authority.authority_token)
        self.world = SimulationWorld()
        self.memory_store = MemoryStore()
        self.fact_store = FactStore()
        self.belief_store = BeliefStore()
        self.reflection_store = ReflectionStore()
        self.sim_event_queue = EventQueue()
        self.graph_store = GraphStore()
        self.meta_store = MetaStore()
        self.plan_store = PlanStore()
        self.long_horizon_planner = LongHorizonPlanner(plan_store=self.plan_store)
        self.executive_store = ExecutiveStore()
        self.strategy_store = StrategyStore()
        self.strategy_selection_store = StrategySelectionStore()
        self.policy_store = PolicyStore()
        self.executive_evaluation_store = ExecutiveEvaluationStore()
        self.bias_plan_store = BiasPlanStore()
        self.adaptation_store = AdaptationStore()
        self.executive_optimization_store = ExecutiveOptimizationStore()
        self.executive_policy_store = ExecutivePolicyStore()
        self.predictive_store = PredictiveStore()
        self.predictive_store = PredictiveStore()
        self.executive_feedback_store = ExecutiveFeedbackStore()
        # Equilibrium analysis, attractor classification, and adaptive controller
        self.equilibrium_analyzer = EquilibriumAnalyzer()
        self.attractor_classifier = AttractorClassifier()
        self.adversarial_controller = AdversarialController()
        self._control_signal = ControlSignal()
        self._adversary_scale = 1.0
        self._world_history = []  # list of world snapshots for analysis
        self.projections = []
        self._pending_signals: list[dict] = []
        self.invariant_validator = invariant_validator or InvariantValidator(ledger=self.ledger)
        self.snapshot_engine = SnapshotEngine(interval=snapshot_interval, ledger=self.ledger, invariant_validator=self.invariant_validator)
        self.transition_auditor = TransitionAuditor(ledger=self.ledger)
        self.profiler = TickProfiler(ledger=self.ledger)
        self.perf_budgets = PerformanceBudgets()
        self.perf_metrics = PerformanceMetrics(ledger=self.ledger)
        self.scenario_config = scenario_config
        self.counterfactual_store = CounterfactualStore()
        self.graph_store = GraphStore()
        
        # Diagnostics & Observability
        from scrubin.diagnostics.sensors import ObservationEngine
        from scrubin.diagnostics.queues import DiagnosticQueue
        self.observation_engine = ObservationEngine(seed=seed)
        self.world.diagnostic_queue = DiagnosticQueue()
        
        self.scenario_engine = None
        if scenario_config:
            from scrubin.scenarios.engine import ScenarioEngine
            self.scenario_engine = ScenarioEngine(scenario_config, self)

        self.bus.subscribe("complication_signal", self._handle_signal)
        self.bus.subscribe("complication", self._handle_complication)

    def register_projection(self, projection):
        self.projections.append(projection)
        self.ledger.add_listener(projection.apply)

    def _handle_signal(self, event):
        if event.tick == self.tick_count:
            self._pending_signals.append(event.payload)

    def _handle_complication(self, event):
        if event.tick == self.tick_count:
            self._pending_signals.append({
                "tick": event.payload.get("tick", 0),
                "complication": event.payload.get("complication"),
                "severity": event.payload.get("severity", "moderate"),
            })

    def setup(self):
        if self.config.has_overrides:
            print(f"[Orchestrator] profile={self.active_profile} loaded {len(self.config._overrides)} patch override(s)")
        self.bus.publish(
            "system.boot",
            {"seed": self.seed, "patient_profile": self.patient_profile.id, "mode": self.mode},
            priority=10,
        )

    def register_agent(self, event_type, handler):
        self.bus.subscribe(event_type, handler)

    def submit_vitals(self, tick: int, vitals_dict: dict):
        return self.authority.execute_vitals_injection(tick, vitals_dict)

    def tick(self):
        self.tick_count += 1
        self.world.tick = self.tick_count
        self._pending_signals.clear()
        self.profiler.start_tick(self.tick_count)

        self.bus.publish(
            "tick",
            {"tick": self.tick_count},
            priority=0,
        )

        if self.scenario_engine:
            self.scenario_engine.process_tick(self.tick_count)

        result = self.bus.tick()

        self.profiler.start_phase("evolve")
        self._evolve_world()
        self.profiler.end_phase("evolve")

        # Record world snapshot for analysis
        self._world_history.append(self.world.to_dict())

        # Equilibrium analysis
        metrics = self.equilibrium_analyzer.compute_metrics(self._world_history)
        regime = self.attractor_classifier.classify(metrics)
        self._control_signal = self.adversarial_controller.compute_control(metrics, regime)

        # Apply control adjustments to world state
        self._apply_control()
        decision_output = None
        if self.decision_engine is not None:
            from scrubin.decision.engine import DecisionEngine as _DE
            if isinstance(self.decision_engine, _DE):
                if self.mode == "autonomous":
                    self.profiler.start_phase("planner")
                    intent = self._generate_and_execute_intent()
                    self.profiler.end_phase("planner")
                    if intent is not None:
                        decision_output = {
                            "executed": True,
                            "action": intent.name,
                            "target": intent.target,
                        }
                if self.mode == "interactive":
                    options = self.decision_engine.generate_options(self.ledger.all(), self.tick_count)
                    options_dicts = [self.decision_engine.option_to_dict(o) for o in options]
                    self.ledger.log(
                        "decision_options",
                        {"options": options_dicts, "tick": self.tick_count, "mode": self.mode},
                        tick=self.tick_count,
                    )
                    decision_output = {"options": options_dicts}

            if not isinstance(self.decision_engine, _DE) if self.decision_engine is not None else False:
                options = self.decision_engine.generate_options(self.ledger.all(), self.tick_count)
                options_dicts = [self.decision_engine.option_to_dict(o) for o in options]
                self.ledger.log(
                    "decision_options",
                    {"options": options_dicts, "tick": self.tick_count},
                    tick=self.tick_count,
                )
                print(f"[DecisionEngine] → Generated {len(options)} options for tick {self.tick_count}")
                for o in options_dicts:
                    print(f"[DecisionEngine] - {o['id']}: {o['label']} (risk={o['risk_level']}, target={o.get('target_complication', '')})")
                decision_output = {"options": options_dicts}

        # Meta‑learning aggregation – generate deterministic meta‑patterns
        # Deterministic meta‑pattern aggregation
        update_meta_patterns(
            reflection_store=self.reflection_store,
            counterfactual_store=self.counterfactual_store,
            knowledge_graph=self.graph_store,
            meta_store=self.meta_store,
        )
        # Deterministic long‑horizon planning is deferred until after predictive state generation
        # The planner will be invoked later using executive policy decisions and predictive states.

        # Executive update – generate deterministic goals from meta‑patterns, beliefs, and plans
        update_executive(self.meta_store, self.belief_store, self.plan_store, self.executive_store)
        # Schedule pending goals deterministically
        scheduled_goals = schedule_goals(self.executive_store, self.tick_count)
        # Monitor and update goal statuses based on world progress
        monitor_goals(self.tick_count, self.executive_store, self.plan_store, scheduled_goals)
        update_strategies(self.plan_store, self.executive_store, self.strategy_store)
        update_strategy_selection(self.executive_store, self.strategy_store, self.belief_store, self.reflection_store, self.strategy_selection_store)
        # Run full deterministic cognitive pipeline (graph, meta, executive) for audit
        update_executive_evaluations(self.strategy_selection_store, self.executive_store, self.plan_store, self.strategy_store, self.belief_store, self.reflection_store, self.counterfactual_store, self.executive_evaluation_store)
        policy_recommendations = run_policy_refinement(self.executive_evaluation_store, self.strategy_store)
        # Update policy profiles based on executive evaluations
        update_policy_profiles(self.executive_evaluation_store, self.strategy_store, self.strategy_selection_store, self.policy_store)
        # Generate strategy bias from policy profiles
        self.strategy_biases = generate_strategy_bias(self.policy_store)
        update_bias_plan_candidates(
            self.executive_store,
            self.strategy_store,
            self.strategy_selection_store,
            self.policy_store,
            self.strategy_biases,
            self.bias_plan_store,
        )
        self.executive_rankings = compute_executive_ranking(self.bias_plan_store)
        # Executive feedback loop – evaluate bias-aware planning outcomes
        update_executive_feedback(
            self.executive_evaluation_store,
            self.policy_store,
            self.bias_plan_store,
            self.executive_feedback_store,
        )
        # Generate adaptation signals based on feedback
        self.adaptation_signals = generate_adaptation_signals(self.executive_feedback_store)
        # Update persistent adaptation profiles from feedback
        update_adaptation_profiles(
            self.executive_feedback_store,
            self.policy_store,
            self.adaptation_store,
        )
        # Generate adaptation biases for downstream planning
        self.adaptation_biases = generate_adaptation_biases(self.adaptation_store)
        self.self_improvement_signals = generate_self_improvement_signals(self.executive_optimization_store)
        # Executive policy arbitration – decide final strategy for each goal
        update_executive_policy(
            self.executive_store,
            self.strategy_selection_store,
            self.policy_store,
            self.adaptation_store,
            self.executive_optimization_store,
            self.strategy_store,
            self.self_improvement_signals,
            self.executive_policy_store,
        )
        self.executive_policy_decisions = self.executive_policy_store.decisions
        # Generate deterministic predictive states for future horizons
        from scrubin.cognition.predictive_engine import update_predictive_states
        update_predictive_states(
            executive_policy_store=self.executive_policy_store,
            counterfactual_store=self.counterfactual_store,
            graph_store=self.graph_store,
            adaptation_store=self.adaptation_store,
            policy_store=self.policy_store,
            predictive_store=self.predictive_store,
        )
        # Deterministic long‑horizon planning using executive policy decisions
        actions = [
            {
                "action_id": decision.id,
                "action_name": decision.selected_strategy_id,
                "expected_reward": decision.arbitration_score,
                "confidence": decision.confidence,
            }
            for decision in self.executive_policy_store.decisions
        ]
        self.long_horizon_planner.generate_plan(self.tick_count, actions)
        run_cognitive_pipeline(
            self.world,
            self.memory_store,
            self.fact_store,
            self.belief_store,
            self.reflection_store,
            self.graph_store,
            self.counterfactual_store,
            self.meta_store,
            self.plan_store,
            self.executive_store,
        )
        
        profile = self.profiler.end_tick()
        self.perf_metrics.record_tick(TickMetrics(
            tick=profile.tick,
            tick_duration_ms=profile.tick_duration_ms,
            evolve_duration_ms=profile.evolve_duration_ms,
            planner_duration_ms=profile.planner_duration_ms,
            validator_duration_ms=profile.validator_duration_ms,
        ))
        budget_violation = self.perf_budgets.check_tick_budget(profile.tick_duration_ms)
        if budget_violation:
            self.perf_metrics.record_budget_violation(budget_violation)

        return {
            "orchestrator_tick": self.tick_count,
            "bus": result,
            "decision": decision_output,
        }

    def _evolve_world(self):
        prev_state = self.world.to_dict()
        prev_mortality = self.world.mortality_risk

        # ---------- Deterministic physiology evolution ----------
        # Build an immutable WorldState snapshot required by the physiology engine.
        from scrubin.world.state import WorldState, PhysiologicalState, CardiovascularState, RespiratoryState, ComplicationWorldState
        vitals = self.world.physiology.vitals
        cardio = CardiovascularState(
            map=vitals.get("map", 100.0),
            heart_rate=vitals.get("heart_rate", 80.0),
        )
        resp = RespiratoryState(
            spo2=vitals.get("spo2", 98.0),
        )
        phys_state = PhysiologicalState(vitals=vitals, cardiovascular=cardio, respiratory=resp)
        immutable_world = WorldState(
            tick=self.world.tick,
            physiology=phys_state,
            complications=ComplicationWorldState(),
            hidden_effects=tuple(),
        )
# Generate all deterministic events for this tick and process them in a single pass
# 1. Physiology events (including timeline)
phy_events, phy_timeline = generate_physiology_events(immutable_world, SimulationRNG(self.seed))

# 2. Disease progression events
from scrubin.physiology.disease_progression import DiseaseProgressionEngine
disease_engine = DiseaseProgressionEngine()
disease_events = disease_engine.generate_events(self.world)

# 3. Medication PK/PD events
from scrubin.physiology.pkpd_engine import PKPDEngine
pkpd_engine = PKPDEngine()
pkpd_events = pkpd_engine.generate_events(self.world)

# 4. Hidden‑state propagation events
from scrubin.engine.hidden_state_propagation import apply_hidden_state_propagation
hidden_events = apply_hidden_state_propagation(self.world)

# 5. Complication generation events
comp_events = generate_complication_events(self.world)

# Consolidate events preserving the original order
all_events = []
all_events.extend(phy_events)
all_events.extend(disease_events)
all_events.extend(pkpd_events)
all_events.extend(hidden_events)
all_events.extend(comp_events)

# Enqueue events
for ev in all_events:
    self.sim_event_queue.add(ev)

# Process the accumulated events once
from scrubin.events.event_processor import process_events
self.world, self.sim_event_queue = process_events(self.world, self.sim_event_queue, authority=self.authority)

# Apply any physiology timeline events after processing (they are not part of the event queue)
        if phy_timeline:
    self.world.append_timeline(phy_timeline)

        # Recalculate derived clinical metrics (mortality, SOFA, NEWS2)
        _recalculate_derived_metrics(self.world)

        # ---------- Episodic Memory Encoding ----------
        # Combine deterministic events generated this tick
        events_this_tick = all_events
        episode = encode_events_to_episode(events_this_tick, self.world, self.tick_count)
        self.memory_store.add_episode(episode)
        # Update semantic facts from the new episode
        from scrubin.cognition.fact_builder import process_episode
        process_episode(episode, self.fact_store)
        # Update reflections from the updated belief store
        from scrubin.cognition.reflection_engine import update_reflections_from_beliefs
        update_reflections_from_beliefs(self.belief_store, self.reflection_store)

        # ---------- Observability ----------
        self.world.observed_vitals = self.observation_engine.get_observed_vitals(self.world.physiology.vitals)
        newly_completed = self.world.diagnostic_queue.update(self.tick_count)
        for task in newly_completed:
            self.bus.publish("diagnostic_result", task.to_dict())

        # ---------- Validation ----------
        self.profiler.start_phase("validator")
        self.invariant_validator.validate(self.world)
        self.profiler.end_phase("validator")

        # ---------- Auditing ----------
        self.profiler.start_phase("audit")
        self.transition_auditor.record(
            tick=self.tick_count,
            source_event="world.evolve_deterministic",
            affected_system="simulation_world",
            before=prev_state,
            after=self.world.to_dict(),
        )
        self.profiler.end_phase("audit")

        self.profiler.start_phase("hash")
        from scrubin.replay.hash import world_hash
        tick_hash = world_hash(self.world)
        self.ledger.log(
            "world_hash_generated",
            {"tick": self.tick_count, "hash": tick_hash},
            tick=self.tick_count,
        )
        self.profiler.end_phase("hash")

        if self.snapshot_engine.should_snapshot(self.tick_count):
            self.profiler.start_phase("snapshot")
            self.snapshot_engine.capture(self.world, self.tick_count)
            self.profiler.end_phase("snapshot")

        for organ_name, organ in [("cardiovascular", self.world.organ_state.cardiovascular),
                                  ("respiratory", self.world.organ_state.respiratory),
                                  ("renal", self.world.organ_state.renal)]:
            if organ.health < 0.3:
                self.bus.publish("organ_failure", {"organ": organ_name, "health": organ.health, "tick": self.tick_count})
        
        if abs(self.world.mortality_risk - prev_mortality) > 0.05:
            self.bus.publish("mortality_risk_change", {"new_risk": self.world.mortality_risk, "delta": self.world.mortality_risk - prev_mortality, "tick": self.tick_count})
            
        # 5. Check Resource Exhaustion
        for res_name, res in self.world.resource_manager.resources.items():
            if res.available == 0:
                self.bus.publish("resource_exhaustion", {"resource": res_name, "tick": self.tick_count})
        
    # 6. Meta‑learning aggregation – deterministic pattern extraction
    

    def _apply_control(self):
        """Apply control signal – currently a no‑op placeholder.

        To keep the orchestrator fully deterministic via the event pipeline, any
        state adjustments driven by the control signal should be emitted as
        deterministic events. This implementation is intentionally empty until a
        dedicated CONTROL_EVENT is defined and handled in the event processor.
        """
        # No direct state mutation performed here.
        pass

    def _generate_and_execute_intent(self) -> ActionIntent | None:
        if not self._pending_signals:
            return None

        decision = self.decision_engine.decide(self.world, self.ledger.all(), self.tick_count)
        
        # Phase 6: Publish Planning Results
        if hasattr(decision, "planning_result"):
            res = decision.planning_result
            self.bus.publish("decision_trace", {
                "action": res.selected_action,
                "expected_utility": res.expected_utility,
                "projected_mortality": res.projected_mortality,
                "explored_nodes": res.explored_nodes,
                "search_depth": res.search_depth,
                "reasoning_trace": res.reasoning_trace,
                "tick": self.tick_count
            })
            
        if decision.action.type != "procedure":
            return None

        intent = ActionIntent(
            id=f"intent-{uuid.uuid4().hex[:8]}",
            type=decision.action.type,
            name=decision.action.name,
            target=decision.action.target,
            priority=float(decision.score),
            confidence=decision.action.confidence,
            source="engine",
            reasoning="; ".join(decision.reasoning),
            metadata={
                "severity": decision.action.severity,
                "risk_level": decision.action.risk_level,
                "expected_effect": decision.action.expected_effect,
            },
        )

        if self.decision_validator is not None:
            from scrubin.decision.validator import DecisionValidator as _DV
            if isinstance(self.decision_validator, _DV):
                decision_dict = {
                    "action": {
                        "type": decision.action.type,
                        "name": decision.action.name,
                        "target": decision.action.target,
                    }
                }
                validation = self.decision_validator.validate(
                    seed=self.seed,
                    current_tick=self.tick_count,
                    profile_name=self.active_profile,
                    decision_dict=decision_dict,
                )
                if validation.verdict != "strong_improvement" and validation.verdict != "weak_improvement":
                    print(f"[Orchestrator] validation rejected: verdict={validation.verdict} confidence={validation.confidence}")
                    return None

        # Convert the intent into a deterministic Action event and queue it
        from scrubin.events.action_helper import create_action_event
        from scrubin.events.event_processor import process_events
        # Build the event – deterministic id based on tick and intent.id
        action_event = create_action_event(tick=self.tick_count, intent=intent, source="engine")
        self.sim_event_queue.add(action_event)
        # Process the queue (authority will execute the intent inside the processor)
        self.world, self.sim_event_queue = process_events(self.world, self.sim_event_queue, authority=self.authority)
        # Determine whether the intent was executed by inspecting the authority log
        executed = any(
            ee.intent_id == intent.id and ee.outcome == "executed"
            for ee in self.authority.execution_log
        )
        if executed:
            print(f"[ActionAuthority] tick={self.tick_count} executed={intent.name} for={intent.target}")
        else:
            print(f"[ActionAuthority] tick={self.tick_count} rejected={intent.name} (not executed)")
        return intent if executed else None

    def reset(self):
        self.tick_count = 0
        self.ledger = EventLedger()
        self.bus = EventBus(ledger=self.ledger)
        self.authority = ActionAuthority(
            bus=self.bus,
            ledger=self.ledger,
            state=self,
        )
        self.bus.set_authority_token(self.authority.authority_token)
        self.world = SimulationWorld()
        self.memory_store = MemoryStore()
        self.fact_store = FactStore()
        self.belief_store = BeliefStore()
        self.reflection_store = ReflectionStore()
        self.sim_event_queue = EventQueue()
        self.graph_store = GraphStore()
        self.meta_store = MetaStore()
        self.plan_store = PlanStore()
        self.long_horizon_planner = LongHorizonPlanner(plan_store=self.plan_store)
        self.executive_store = ExecutiveStore()
        self.strategy_store = StrategyStore()
        self.strategy_selection_store = StrategySelectionStore()
        self.policy_store = PolicyStore()
        self.executive_evaluation_store = ExecutiveEvaluationStore()
        self.bias_plan_store = BiasPlanStore()
        self.adaptation_store = AdaptationStore()
        self.executive_optimization_store = ExecutiveOptimizationStore()
        self.executive_policy_store = ExecutivePolicyStore()
        self.predictive_store = PredictiveStore()
        self.predictive_store = PredictiveStore()
        self.executive_feedback_store = ExecutiveFeedbackStore()
        self._pending_signals.clear()
        self.invariant_validator = InvariantValidator(ledger=self.ledger)
        self.snapshot_engine = SnapshotEngine(ledger=self.ledger, invariant_validator=self.invariant_validator)
        self.transition_auditor = TransitionAuditor(ledger=self.ledger)
        self.profiler = TickProfiler(ledger=self.ledger)
        self.perf_budgets = PerformanceBudgets()
        self.perf_metrics = PerformanceMetrics(ledger=self.ledger)
        if self.decision_engine is not None:
            self.decision_engine._decision_log.clear()
            self.counterfactual_store = CounterfactualStore()
            self.graph_store = GraphStore()

    def inject_action(self, action: dict):
        action_type = action.get("type", "unknown")
        if action_type == "vitals_update":
            vitals = action.get("vitals", action.get("metadata", {}).get("vitals", {}))
            tick = action.get("tick", self.tick_count)
            result = self.authority.execute_vitals_injection(tick, vitals)
            return {"injected": "vitals_update", "executed": result.get("vitals_injected", False), "payload": action}

        if action_type in ("procedure", "state_transition"):
            intent = ActionIntent(
                id=f"intent-inject-{uuid.uuid4().hex[:8]}",
                type=action_type,
                name=action.get("name", action_type),
                target=action.get("target", ""),
                priority=action.get("priority", 0.0),
                confidence=action.get("confidence", 0.0),
                source="inject",
                reasoning=action.get("reasoning", ""),
                metadata=action.get("metadata", {}),
            )
            # Convert the intent into a deterministic Action event and enqueue it
            from scrubin.events.action_helper import create_action_event
            from scrubin.events.event_processor import process_events
            action_event = create_action_event(tick=self.tick_count, intent=intent, source="inject")
            self.sim_event_queue.add(action_event)
            # Process the queued event – authority will execute the intent
            self.world, self.sim_event_queue = process_events(self.world, self.sim_event_queue, authority=self.authority)
            executed = any(
                ee.intent_id == intent.id and ee.outcome == "executed"
                for ee in self.authority.execution_log
            )
            return {"injected": action_type, "executed": executed, "payload": action}

        event_type = action_type
        payload = {k: v for k, v in action.items() if k != "type"}
        self.bus.publish(event_type, payload)
        return {"injected": event_type, "payload": payload}

    def apply_user_decision(self, option_id: str, target: str = ""):
        from scrubin.decision.engine import DecisionEngine as _DE
        if self.decision_engine is None or not isinstance(self.decision_engine, _DE):
            return {"executed": False, "reason": "no decision engine"}

        intent = self.decision_engine.resolve_option_to_intent(option_id, target, tick=self.tick_count)
        if intent is None:
            return {"executed": False, "reason": f"unknown option: {option_id}"}

        if intent.type == "procedure":
            # Queue the user decision as an Action event and process it
            from scrubin.events.action_helper import create_action_event
            from scrubin.events.event_processor import process_events
            action_event = create_action_event(tick=self.tick_count, intent=intent, source="user_decision")
            self.sim_event_queue.add(action_event)
            # Process the queued event – authority will execute the intent
            self.world, self.sim_event_queue = process_events(self.world, self.sim_event_queue, authority=self.authority)
            # Check execution outcome via the authority log
            executed = any(
                ee.intent_id == intent.id and ee.outcome == "executed"
                for ee in self.authority.execution_log
            )
            if executed:
                print(f"[Orchestrator] user decision → procedure={intent.name} for={intent.target}")
                return {
                    "executed": True,
                    "action": intent.name,
                    "target": intent.target,
                    "reason": "executed_by_authority",
                }

        self.ledger.log(
            "decision_execution",
            {
                "executed": False,
                "action": intent.name,
                "tick": self.tick_count,
                "source": "user_decision",
                "reason": f"non-procedure action type: {intent.type}",
            },
            tick=self.tick_count,
        )
        return {"executed": False, "action": intent.name, "reason": f"action type: {intent.type}"}

    def force_complication(self, complication: str, severity: str = "moderate", at_tick: int = None):
        if ComplicationRegistry.get(complication) is None:
            return {"forced": False, "reason": f"unknown complication: {complication}"}
        self.bus.publish(
            "complication",
            {"tick": at_tick or self.tick_count, "complication": complication, "severity": severity},
        )
        return {"forced": complication, "severity": severity, "at_tick": at_tick or self.tick_count}
    def run_counterfactual(self, source_episode_id: str, hypothetical_event: SurgicalEvent) -> CounterfactualResult:
        '''Execute a deterministic counterfactual scenario based on a hypothetical event.

        The scenario is stored in ``self.counterfactual_store`` and the result is returned.
        '''
        scenario = CounterfactualScenario.create(
            source_episode_id=source_episode_id,
            starting_tick=self.world.tick,
            hypothetical_event=hypothetical_event,
            confidence=1.0,
        )
        result = _run_counterfactual(
            scenario=scenario,
            world_snapshot=self.world,
            memory_store=self.memory_store,
            fact_store=self.fact_store,
            belief_store=self.belief_store,
            reflection_store=self.reflection_store,
            graph_store=self.graph_store,
        )
        self.counterfactual_store.add(scenario, result)
        return result
