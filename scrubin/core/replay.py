from scrubin.models.types import SimulationState, Vitals, ComplicationState


class ReplayEngine:
    def __init__(self, ledger, invariant_validator=None):
        self.ledger = ledger
        self.invariant_validator = invariant_validator

    def rebuild_state(self, target_tick: int) -> SimulationState:
        state = SimulationState(status="replayed")
        events = self.ledger.all()
        for event in events:
            if event.tick > target_tick:
                break
            state = self._apply_event(state, event)
        return state

    def _apply_event(self, state: SimulationState, event) -> SimulationState:
        if event.type == "system.boot":
            state.seed = event.payload.get("seed", 0)
            state.patient_profile = event.payload.get("patient_profile", "standard")
            state.mode = event.payload.get("mode", "autonomous")
        elif event.type == "tick":
            state.tick = event.payload.get("tick", 0)
        elif event.type == "state.snapshot":
            snapshot = event.payload.get("state", {})
            if isinstance(snapshot, dict):
                state = SimulationState.from_dict(snapshot)
        elif event.type == "vitals_update":
            vitals_dict = event.payload.get("vitals", {})
            state.with_vitals(Vitals.from_dict(vitals_dict) if vitals_dict else state.vitals)
        elif event.type == "complication":
            comp_id = event.payload.get("complication", "")
            severity = event.payload.get("severity", "moderate")
            onset_tick = event.payload.get("tick", 0)
            if comp_id:
                state.add_complication(ComplicationState(
                    id=comp_id,
                    severity=severity,
                    onset_tick=onset_tick,
                ))
        elif event.type == "complication_escalation":
            comp_id = event.payload.get("complication", "")
            severity = event.payload.get("severity", "moderate")
            if comp_id:
                state.update_complication(comp_id, severity=severity)
        elif event.type == "procedure":
            proc_name = event.payload.get("procedure", "")
            if proc_name:
                state.add_procedure(proc_name)
        elif event.type == "recovery":
            target = event.payload.get("target", "")
            if target:
                state.update_complication(target, lifecycle="recovering")
        return state

    def verify(self, world, original_hash: str) -> dict:
        if self.invariant_validator is not None:
            violations = self.invariant_validator.validate_soft(world)
        else:
            violations = []
        from scrubin.replay.hash import world_hash
        replayed_hash = world_hash(world)
        matched = replayed_hash == original_hash
        return {
            "original_hash": original_hash,
            "replayed_hash": replayed_hash,
            "matched": matched,
            "invariant_violations": len(violations),
        }

    def trace(self, event_id: int):
        chain = []
        events = self.ledger.all()
        current = next((e for e in events if e.id == event_id), None)
        while current:
            chain.append(current)
            pid = current.parent_id
            if pid is None:
                break
            current = next((e for e in events if e.id == pid), None)
        return list(reversed(chain))
