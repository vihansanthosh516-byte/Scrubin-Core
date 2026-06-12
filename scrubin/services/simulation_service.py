import uuid
import asyncio
import random
from dataclasses import replace

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ProcedureAgent
from scrubin.patient.profile import PatientProfile, PATIENT_PROFILES, STANDARD_PATIENT
from scrubin.tester.profiles.registry import PROFILES, StressProfile
from scrubin.procedures.registry import BASE_DIR

from scrubin.projections.state import StateProjection
from scrubin.projections.event import EventProjection
from scrubin.projections.decision import DecisionProjection
from scrubin.api.mappers import map_option_to_dto, StateSnapshotDTO
from scrubin.models.intents import ActionIntent
from scrubin.engine.procedure import ProcedurePhase
from scrubin.engine.procedural_phase_engine import ProceduralPhaseEngine
from scrubin.decision.dynamic_actions import generate_dynamic_options
from scrubin.decision.consequence_engine import generate_consequence_events

class SimulationService:
    def __init__(self, session_id: str, seed: int, profile_name: str, patient_profile_id: str, mode: str, procedure_id: str | None = None, variant_id: str | None = None):
        self.session_id = session_id
        self.seed = seed
        self.profile_name = profile_name
        self.patient_profile_id = patient_profile_id
        self.mode = mode
        self.procedure_id = procedure_id
        self.variant_id = variant_id
        
        self.profile = PROFILES.get(profile_name, StressProfile)()
        self.patient_profile = PATIENT_PROFILES.get(patient_profile_id, STANDARD_PATIENT)
        
        random.seed(seed)
        config = ConfigLayer(active_profile=profile_name)
        
        self.orchestrator = Orchestrator(
            seed=seed,
            config=config,
            active_profile=profile_name,
            patient_profile=self.patient_profile,
            mode=mode,
        )
        
        # Setup Projections
        self.state_proj = StateProjection(self.patient_profile_id, self.mode)
        self.event_proj = EventProjection()
        self.decision_proj = DecisionProjection()
        
        self.orchestrator.register_projection(self.state_proj)
        self.orchestrator.register_projection(self.event_proj)
        self.orchestrator.register_projection(self.decision_proj)

        # Wire Agents
        SimulationAgent().setup(self.orchestrator)
        self._wire_vitals(self.orchestrator, self.profile, self.patient_profile)
        self._wire_complication(self.orchestrator, self.profile)
        self._wire_signal_agent(self.orchestrator, self.profile)
        self._wire_decision(self.orchestrator)
        
        self.orchestrator.setup()
        # Load a procedure definition (default to "appendectomy" if none specified)
        from scrubin.procedures.registry import get_procedure
        proc_id = procedure_id or "appendectomy"
        try:
            self.procedure = get_procedure(proc_id)
            self._procedure_phases = self.procedure.get("phases", [])
            # Convert raw phase dictionaries into typed ProcedurePhase objects
            self._procedure_phase_objs = [ProcedurePhase.from_dict(p) for p in self._procedure_phases]
        except FileNotFoundError:
            self.procedure = None
            self._procedure_phases = []
            self._procedure_phase_objs = []
            print(f"[PROCEDURE] Procedure '{proc_id}' not found; proceeding without procedure steps")
        else:
            # Initialise the deterministic procedural phase engine with the typed phases.
            self.procedural_phase_engine = ProceduralPhaseEngine({p.id: p for p in self._procedure_phase_objs})
            print(f"[PROCEDURE] Loaded procedure '{self.procedure.get('id')}' with {len(self._procedure_phases)} phases")
        self._apply_variant()
        self.event_queue = asyncio.Queue()
        # Generate initial decision options for interactive sessions so that the first snapshot contains runtime options
        if self.mode == "interactive" and hasattr(self.orchestrator, "decision_engine") and self.orchestrator.decision_engine is not None:
            # Use the decision engine to generate options at tick 0 (pre‑tick)
            options = self.orchestrator.decision_engine.generate_options(self.orchestrator.ledger.all(), self.orchestrator.tick_count)
            options_dicts = [self.orchestrator.decision_engine.option_to_dict(o) for o in options]
            # Log the decision_options event so DecisionProjection captures them
            self.orchestrator.ledger.log(
                "decision_options",
                {"options": options_dicts, "tick": self.orchestrator.tick_count, "mode": self.orchestrator.mode},
                tick=self.orchestrator.tick_count,
            )
            print("[OPTIONS] Generated runtime options:", options_dicts)


    def tick_session(self, steps: int = 1):
        for _ in range(steps):
            self.orchestrator.tick()
        # Emit updated state after ticking
        self._push_snapshot_event()

    def apply_decision(self, option_id: str, target: str = "") -> dict:
        # Frontend decision handling – advance simulation state after applying the user choice
        print(f"[DECISION] Received option_id='{option_id}', target='{target}'")
        if self.mode != "interactive":
            return {"executed": False, "reason": "not interactive mode"}
        result = self.orchestrator.apply_user_decision(option_id, target)
        # Capture the DecisionOption object for later consequence application (before any ticks)
        decision_engine = getattr(self.orchestrator, "decision_engine", None)
        selected_option_obj = None
        if decision_engine and hasattr(decision_engine, "_last_generated_options"):
            for opt in decision_engine._last_generated_options:
                if opt.id == option_id:
                    selected_option_obj = opt
                    break
        # Determine if we should advance the simulation tick:

        # - Executed procedures advance (executed=True)
        # - Monitor/Wait actions (action present) also advance
        # - Unknown option (action missing) should not advance
        should_advance = result.get("executed", False) or bool(result.get("action", ""))
        if should_advance:
            # Advance simulation by one tick (world evolution, complications, new options)
            self.orchestrator.tick()
            print(f"[STATE ADVANCE] Tick advanced to {self.orchestrator.tick_count}")
        # Resolve decision via the orchestrator (complication engine)
        result = self.orchestrator.apply_user_decision(option_id, target)
        # If the orchestrator didn't recognize the option, treat it as a curriculum/procedure step
        proc_opts = self._procedure_options()
        proc_ids = {opt["id"] for opt in proc_opts}
        intent_id = ""
        if not result.get("executed", False) and not result.get("action"):
            if option_id in proc_ids:
                # Create a curriculum intent and execute it
                intent = ActionIntent(
                    id=f"intent-user-{uuid.uuid4().hex[:8]}",
                    type="procedure",
                    name=option_id,
                    target="",
                    priority=0.0,
                    confidence=1.0,
                    source="user_decision",
                    reasoning=f"Curriculum step {option_id}",
                    metadata={},
                )
                exec_result = self.orchestrator.authority.execute(intent)
                result = {
                    "executed": exec_result.executed,
                    "action": intent.name,
                    "target": intent.target,
                    "reason": exec_result.reason,
                }
                intent_id = intent.id
        # Determine if we should advance the simulation tick (any successful action)
        should_advance = result.get("executed", False) or bool(result.get("action"))
        if should_advance:
            self.orchestrator.tick()
            print(f"[STATE ADVANCE] Tick advanced to {self.orchestrator.tick_count}")
        # Capture intent_id of last executed intent if not already set
        if not intent_id and self.orchestrator.authority.execution_log:
            intent_id = self.orchestrator.authority.execution_log[-1].intent_id
        # Apply deterministic consequence of the selected action (if any)
        if selected_option_obj is not None:
            # Determine current phase identifier (optional, for rule‑specific logic)
            phase_id = None
            if getattr(self, "_procedure_phase_objs", None):
                tick = self.state_proj.current_tick if hasattr(self.state_proj, "current_tick") else 0
                phase_idx = min(tick, len(self._procedure_phase_objs) - 1)
                phase_obj = self._procedure_phase_objs[phase_idx]
                phase_id = getattr(phase_obj, "id", None) or getattr(phase_obj, "title", None)
            # Generate deterministic consequence events and enqueue them
            from scrubin.decision.consequence_engine import generate_consequence_events
            from scrubin.events.event_processor import process_events
            conseq_events = generate_consequence_events(self.orchestrator.world, selected_option_obj, phase_id)
            for ev in conseq_events:
                self.orchestrator.sim_event_queue.add(ev)
            # Process the queued consequence events (authority not needed here)
            self.orchestrator.world, self.orchestrator.sim_event_queue = process_events(self.orchestrator.world, self.orchestrator.sim_event_queue, authority=self.orchestrator.authority)
            # Recalculate derived metrics (mortality, SOFA, NEWS2) after applying consequences
            from scrubin.decision.consequence_engine import _recalculate_derived_metrics
            _recalculate_derived_metrics(self.orchestrator.world)
        # Emit updated state snapshot after decision (and possible tick advance)
        self._push_snapshot_event()
        # Log next options for debugging
        next_opts = self.get_options()
        print(f"[NEXT OPTIONS] count={len(next_opts)} ids={[o['id'] for o in next_opts]}")
        return {
            "executed": result.get("executed", False),
            "action": result.get("action", ""),
            "target": result.get("target", ""),
            "reason": result.get("reason", ""),
            "intent_id": intent_id,
        }

    def get_snapshot(self) -> dict:
        state_snap = self.state_proj.get_snapshot()
        return state_snap

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        return self.event_proj.get_recent(limit)

    def get_events_since(self, sequence: int) -> list[dict]:
        return self.event_proj.events_after(sequence)

    def _procedure_options(self) -> list[dict]:
        """Generate procedure‑specific option dicts for the current phase.

        Returns a list of option dicts matching the shape expected by the UI:
        {"id": <str>, "label": <str>, "archetype": "procedure", "expected_impact": {}, "risk_level": "low", "target_complication": ""}
        """
        if not getattr(self, "_procedure_phases", None):
            return []
        # Determine phase based on current tick. Simple mapping: each tick advances to next phase until the last.
        tick = self.state_proj.current_tick if hasattr(self.state_proj, "current_tick") else 0
        # Determine the current procedure phase using the typed objects if available
        if getattr(self, "_procedure_phase_objs", None):
            phase_idx = min(tick, len(self._procedure_phase_objs) - 1)
            phase_obj = self._procedure_phase_objs[phase_idx]
            instructions = phase_obj.required_decisions
        else:
            phase_idx = 0
            instructions = []
        opts = []
        for instr in instructions:
            opt_id = instr.lower().replace(" ", "_")
            opts.append({
                "id": opt_id,
                "label": instr,
                "archetype": "procedure",
                "expected_impact": {},
                "risk_level": "low",
                "target_complication": "",
            })
        if opts:
            print(f"[PROCEDURE] Generated {len(opts)} options for phase '{phase_obj.title if hasattr(self, '_procedure_phase_objs') else 'unknown'}' (index {phase_idx})")
        return opts

    def get_options(self) -> list[dict]:
        # Include dynamic actions based on world state and current phase
        # Base options from the decision engine (complication‑driven)
        decision_snap = self.decision_proj.get_snapshot()
        base_opts_raw = decision_snap.get("options", [])
        # Determine if there is an active complication (affects base options relevance)
        state_snap = self.state_proj.get_snapshot()
        active_comp = state_snap.get("active_complication")
        # Convert raw options to dicts if needed
        if base_opts_raw and isinstance(base_opts_raw[0], dict):
            base_opts = base_opts_raw
        else:
            base_opts = [map_option_to_dto(o).to_dict() for o in base_opts_raw]
        # If no active complication, discard generic monitor/wait fallback options
        if not active_comp:
            base_opts = [opt for opt in base_opts if opt.get("id") not in ("monitor", "wait")]
        # Append procedure‑specific options for the current phase
        proc_opts = self._procedure_options()
        # Determine current phase identifier (optional, for dynamic rules)
        phase_id = None
        if getattr(self, "_procedure_phase_objs", None):
            tick = self.state_proj.current_tick if hasattr(self.state_proj, "current_tick") else 0
            phase_idx = min(tick, len(self._procedure_phase_objs) - 1)
            phase_obj = self._procedure_phase_objs[phase_idx]
            phase_id = getattr(phase_obj, "id", None) or getattr(phase_obj, "title", None)
        # Generate dynamic actions based on world hidden_state and phase
        dynamic_opts = generate_dynamic_options(self.orchestrator.world, phase_id)
        dynamic_dicts = [opt.to_dict() for opt in dynamic_opts]
        # Assemble final option list while avoiding duplicate ids
        existing_ids = {opt["id"] for opt in base_opts if isinstance(opt, dict)}
        combined = base_opts + [opt for opt in proc_opts if opt["id"] not in existing_ids]
        existing_ids.update({opt["id"] for opt in combined})
        combined += [opt for opt in dynamic_dicts if opt["id"] not in existing_ids]
        return combined


    def get_summary(self) -> dict:
        state_snap = self.state_proj.get_snapshot()
        decision_snap = self.decision_proj.get_snapshot()
        
        snap = StateSnapshotDTO(
            tick=state_snap["tick"],
            vitals=state_snap["vitals"],
            active_complication=state_snap["active_complication"],
            last_procedure=state_snap["last_procedure"],
            last_decision=decision_snap["last_decision"],
            last_validation=decision_snap["last_validation"],
            last_execution=decision_snap["last_execution"],
            patient_profile=state_snap["patient_profile"],
            mode=state_snap["mode"],
            options=self.get_options(),
        )
        summary = snap.to_dict()
        # UI expects additional fields beyond the snapshot DTO
        # Current decision index – number of executed decisions so far
        try:
            decision_idx = len(self.orchestrator.authority.execution_log)
        except Exception:
            decision_idx = 0
        summary["current_decision_idx"] = decision_idx
        # Phase information – not currently tracked, set to None for now
        summary["phase"] = None
        # Pending decision placeholder – includes an ID derived from the current tick
        pending_id = f"decision_{self.state_proj.current_tick}" if hasattr(self.state_proj, "current_tick") else f"decision_{self.orchestrator.tick_count}"
        summary["pendingDecision"] = {
            "id": pending_id,
            "phase": self.state_proj.current_tick if hasattr(self.state_proj, "current_tick") else None,
            "options": self.get_options(),
        }
        print(f"[SUMMARY] pendingDecision = {summary['pendingDecision']}")
        return summary

    def current_tick(self) -> int:
        return self.state_proj.current_tick

    def _push_snapshot_event(self):
        """Enqueue a state_snapshot event for WebSocket listeners."""
        try:
            snapshot = self.get_summary()
            self.event_queue.put_nowait({"type": "state_snapshot", "summary": snapshot})
        except Exception as e:
            print(f"[SimulationService] Failed to enqueue state_snapshot: {e}")

    def _wire_vitals(self, orch, profile, patient_profile):
        # Use the production VitalsAgent with the patient profile for realistic vitals
        VitalsAgent(patient_profile).setup(orch)

    def _wire_complication(self, orch, profile):
        from scrubin.tester.runner import _ProfiledComplicationAgent
        _ProfiledComplicationAgent(profile).setup(orch)

    def _wire_signal_agent(self, orch, profile):
        if profile.procedure_enabled:
            ProcedureAgent().setup(orch)
        else:
            from scrubin.tester.runner import _NoOpProcedureAgent
            _NoOpProcedureAgent().setup(orch)

    def _wire_decision(self, orch):
        from scrubin.decision.engine import DecisionEngine
        from scrubin.decision.validator import DecisionValidator
        recovery_window = orch.config.get("procedures.yaml", "recovery_window", 5)
        orch.decision_engine = DecisionEngine(recovery_window=recovery_window)
        orch.decision_validator = DecisionValidator(
            horizons=[1, 3, 5],
            weights={1: 0.2, 3: 0.4, 5: 0.4},
            recovery_window=recovery_window,
        )

    def _apply_variant(self):
        """Apply patient variant overrides if configured."""
        variants = self.procedure.get("patient_variants", []) if self.procedure else []
        if not variants:
            return
        selected = None
        if self.variant_id:
            for v in variants:
                if isinstance(v, dict) and v.get("id") == self.variant_id:
                    selected = v
                    break
            if selected is None:
                return
        else:
            sorted_variants = sorted(variants, key=lambda x: x.get("id", ""))
            selected = sorted_variants[0] if sorted_variants else None
        if not selected:
            return
        # Apply physiology overrides
        phys = selected.get("physiology", {})
        if phys:
            from scrubin.models.types import Vitals
            base_dict = self.patient_profile.baseline_vitals.to_dict()
            merged = {**base_dict, **phys}
            new_vitals = Vitals.from_dict(merged)
            self.patient_profile = replace(self.patient_profile, baseline_vitals=new_vitals)
        # Apply hidden_state overrides
        hidden = selected.get("hidden_state", {})
        if hidden:
            self.orchestrator.world.hidden_state.update(hidden)
        # Apply complication modifiers
        comp_mods = selected.get("complication_modifiers", {})
        if comp_mods:
            new_cp = {**self.patient_profile.complication_probability, **comp_mods}
            self.patient_profile = replace(self.patient_profile, complication_probability=new_cp)

    @classmethod
    def create_session(cls, seed: int, profile_name: str, patient_profile_id: str = "standard", mode: str = "autonomous", procedure_id: str | None = None, variant_id: str | None = None):
        session_id = uuid.uuid4().hex[:12]
        return cls(session_id, seed, profile_name, patient_profile_id, mode, procedure_id, variant_id)

    def reset_session(self):
        # Create a new service instance to replace this one in the manager
        new_svc = SimulationService(
            session_id=self.session_id,
            seed=self.seed,
            profile_name=self.profile_name,
            patient_profile_id=self.patient_profile_id,
            mode=self.mode,
            procedure_id=self.procedure_id,
            variant_id=self.variant_id,
        )
        return new_svc
