import uuid
from typing import Any

from scrubin.core.bus import EventBus
from scrubin.core.ledger import EventLedger
from scrubin.core.config import ConfigLayer
from scrubin.execution.authority import ActionAuthority
from scrubin.models.intents import ActionIntent
from scrubin.patient.profile import PatientProfile, STANDARD_PATIENT
from scrubin.complications.registry import ComplicationRegistry
from scrubin.world.model import SimulationWorld
from scrubin.contracts.validator import InvariantValidator
from scrubin.replay.snapshots import SnapshotEngine
from scrubin.audit.transitions import TransitionAuditor
from scrubin.perf.profiler import TickProfiler
from scrubin.perf.budgets import PerformanceBudgets
from scrubin.perf.metrics import PerformanceMetrics, TickMetrics


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
        vitals = self.world.physiology.vitals
        prev_mortality = self.world.mortality_risk

        self.world.evolve()

        # Update Partial Observability
        self.world.observed_vitals = self.observation_engine.get_observed_vitals(self.world.physiology.vitals)
        newly_completed = self.world.diagnostic_queue.update(self.tick_count)
        for task in newly_completed:
            self.bus.publish("diagnostic_result", task.to_dict())

        self.profiler.start_phase("validator")
        self.invariant_validator.validate(self.world)
        self.profiler.end_phase("validator")

        self.profiler.start_phase("audit")
        self.transition_auditor.record(
            tick=self.tick_count,
            source_event="world.evolve",
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
        
    def _apply_control(self):
        """Apply the latest control signal to the world state.

        Simple deterministic adjustments affect mortality risk and vitals.
        """
        cs = self._control_signal
        # Adjust mortality risk as a proxy for overall stability
        self.world.mortality_risk = max(0.0, self.world.mortality_risk + cs.stability_bias)
        self.world.mortality_risk *= (1.0 - cs.damping_factor)
        # Exploration boost adds a dummy "exploration" vital
        if cs.exploration_boost:
            self.world.physiology.vitals["exploration"] = (
                self.world.physiology.vitals.get("exploration", 0.0) + cs.exploration_boost
            )
        # Store adversary pressure scaling for potential downstream use
        self._adversary_scale = cs.adversary_scale

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

        exec_result = self.authority.execute(intent)
        if exec_result.executed:
            print(f"[ActionAuthority] tick={self.tick_count} executed={intent.name} for={intent.target}")
        else:
            print(f"[ActionAuthority] tick={self.tick_count} rejected={intent.name} reason={exec_result.reason}")
        return intent if exec_result.executed else None

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
        self._pending_signals.clear()
        self.invariant_validator = InvariantValidator(ledger=self.ledger)
        self.snapshot_engine = SnapshotEngine(ledger=self.ledger, invariant_validator=self.invariant_validator)
        self.transition_auditor = TransitionAuditor(ledger=self.ledger)
        self.profiler = TickProfiler(ledger=self.ledger)
        self.perf_budgets = PerformanceBudgets()
        self.perf_metrics = PerformanceMetrics(ledger=self.ledger)
        if self.decision_engine is not None:
            self.decision_engine._decision_log.clear()

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
            result = self.authority.execute(intent)
            return {"injected": action_type, "executed": result.executed, "payload": action}

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
            exec_result = self.authority.execute(intent)
            if exec_result.executed:
                print(f"[Orchestrator] user decision → procedure={intent.name} for={intent.target}")
                return {
                    "executed": exec_result.executed,
                    "action": intent.name,
                    "target": intent.target,
                    "reason": exec_result.reason,
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
