import random

from scrubin.complications.registry import ComplicationRegistry
from scrubin.core.config import ConfigLayer
from scrubin.models.types import ComplicationSeverity, ComplicationState
from scrubin.clinical.lifecycle import ComplicationLifecycle, ComplicationStatus


class ComplicationAgent:
    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        config = getattr(orchestrator, 'config', None) or ConfigLayer()
        self._prob = config.get("agents/complication.py", "complication_prob", 0.15)
        self._lifecycles: dict[str, ComplicationLifecycle] = {}
        self._complication_ids = ComplicationRegistry.get_ids()
        orchestrator.register_agent("tick", self._on_tick)

    def _determine_initial_severity(self, complication_id: str) -> ComplicationSeverity:
        import random as _r
        roll = _r.random()
        if roll < 0.5:
            return "mild"
        elif roll < 0.85:
            return "moderate"
        else:
            return "severe"

    def _maybe_escalate(self, comp_state: ComplicationState, tick: int) -> ComplicationState | None:
        escalation = ComplicationRegistry.escalation_for(comp_state.id)
        if escalation is None or escalation.next is None:
            return None
        if random.random() < escalation.probability:
            return ComplicationState(
                id=comp_state.id,
                severity=escalation.next,
                onset_tick=comp_state.onset_tick,
            )
        return None

    def _on_tick(self, event) -> None:
        tick = event.payload.get("tick", 0)
        
        vitals = {}
        if hasattr(self._orchestrator, 'projections') and 'state' in self._orchestrator.projections:
            snap = self._orchestrator.projections['state'].get_snapshot()
            vitals = snap.get('vitals', {})
            
        # Get interventions (procedures performed recently)
        # Ideally from projection. Let's simplify and say we read from ledger or projection
        interventions = []
        if hasattr(self._orchestrator, 'projections') and 'state' in self._orchestrator.projections:
            snap = self._orchestrator.projections['state'].get_snapshot()
            if snap.get('last_procedure'):
                interventions.append(snap['last_procedure']['procedure'])

        # Evaluate existing lifecycles
        for comp_id, lifecycle in self._lifecycles.items():
            transition_event = lifecycle.evaluate(tick, vitals, interventions)
            if transition_event:
                print(f"[ComplicationAgent] tick={tick} {comp_id} transition: {transition_event.from_status} → {transition_event.to_status} ({transition_event.reason})")
                self._orchestrator.bus.publish(
                    "complication_transition",
                    {
                        "tick": tick,
                        "complication": comp_id,
                        "from_status": transition_event.from_status.value,
                        "to_status": transition_event.to_status.value,
                        "reason": transition_event.reason
                    }
                )
                if transition_event.to_status == ComplicationStatus.ESCALATING:
                    # Also publish the old style escalation for backwards compatibility with tests
                    self._orchestrator.bus.publish(
                        "complication_escalation",
                        {"tick": tick, "complication": comp_id, "severity": "severe", "onset_tick": lifecycle.start_tick},
                    )

        if random.random() < self._prob and not self._lifecycles:
            complication = random.choice(self._complication_ids)
            severity = self._determine_initial_severity(complication)
            lifecycle = ComplicationLifecycle(complication, tick, severity)
            self._lifecycles[complication] = lifecycle
            self._orchestrator.bus.publish(
                "complication",
                {"tick": tick, "complication": complication, "severity": severity},
            )
            print(f"[ComplicationAgent] tick={tick} complication={complication} severity={severity}")
        else:
            print(f"[ComplicationAgent] tick={tick} no complication")

    @property
    def complications(self) -> list[ComplicationState]:
        return [
            ComplicationState(id=lc.name, severity=lc.severity, onset_tick=lc.start_tick)
            for lc in self._lifecycles.values() if lc.status not in (ComplicationStatus.RESOLVED, ComplicationStatus.LATENT)
        ]
