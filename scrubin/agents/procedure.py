import random

from scrubin.complications.registry import ComplicationRegistry
from scrubin.core.config import ConfigLayer
from scrubin.decision.engine import _determine_severity


PROCEDURE_EFFECT_MAP = {
    "blood_transfusion": {"bp_systolic": 10, "spo2": 5, "heart_rate": -5},
    "intubation": {"spo2": 5, "heart_rate": -3},
    "ventilator_adjustment": {"spo2": 3},
    "central_line": {"bp_systolic": 5, "bp_diastolic": 3},
    "surgical_intervention": {"temperature": -0.4, "heart_rate": -4},
    "oxygen_therapy": {"spo2": 3, "heart_rate": -2},
    "iv_fluids": {"bp_systolic": 5, "heart_rate": -3},
    "antibiotics": {"temperature": -0.3, "heart_rate": -3},
    "vasopressors": {"bp_systolic": 15, "heart_rate": 8},
    "airway_adjuncts": {"spo2": 4, "heart_rate": -3},
    "emergency_airway": {"spo2": 8, "heart_rate": -5},
    "bag_mask": {"spo2": 4, "heart_rate": -4},
    "iron_supplement": {"spo2": 1, "heart_rate": -2},
    "positioning": {"spo2": 2, "heart_rate": -2},
    "monitor": {},
}

RECOVERY_SPREAD_TICKS = 3


class ComplicationSignalAgent:
    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        config = getattr(orchestrator, 'config', None) or ConfigLayer()
        self._trigger_mode = config.get("agents/procedure.py", "procedure_trigger", "complication_gated")
        self._latest_vitals = {}
        orchestrator.register_agent("complication", self._on_complication)
        orchestrator.register_agent("vitals_update", self._on_vitals)

    def _on_vitals(self, event) -> None:
        self._latest_vitals = event.payload.get("vitals", {})

    def _on_complication(self, event) -> None:
        tick = event.payload.get("tick", 0)
        complication = event.payload.get("complication")
        severity = event.payload.get("severity", "moderate")
        vitals = self._latest_vitals
        computed_severity = _determine_severity(complication, vitals) if vitals else severity
        self._orchestrator.bus.publish(
            "complication_signal",
            {
                "tick": tick,
                "complication": complication,
                "severity": computed_severity,
                "vitals_snapshot": vitals.copy() if vitals else {},
            },
        )
        print(f"[ComplicationSignalAgent] tick={tick} signal={complication} severity={computed_severity}")


class ProcedureAgent(ComplicationSignalAgent):
    pass
