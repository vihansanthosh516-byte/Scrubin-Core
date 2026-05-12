import random

from scrubin.agents.procedure import ComplicationSignalAgent, PROCEDURE_EFFECT_MAP, RECOVERY_SPREAD_TICKS
from scrubin.agents.vitals import VitalsAgent
from scrubin.improvement.patches import Patch


def _directional_vitals(tick, procedure_name, ranges, base_vitals=None):
    vitals = {}
    for key, (lo, hi) in ranges.items():
        current = base_vitals.get(key, (lo + hi) / 2) if base_vitals else (lo + hi) / 2
        effects = PROCEDURE_EFFECT_MAP.get(procedure_name, {})
        effect = effects.get(key, 0.0)
        target = min(hi, max(lo, current + effect))
        bias = (target - current) * 0.6
        vitals[key] = round(max(lo, min(hi, current + bias)), 2)
    return vitals


class EnsurePostProcedureVitals:
    def __init__(self, wrapped_agent: ComplicationSignalAgent):
        self._wrapped = wrapped_agent
        self._procedures = []
        self._orchestrator = None

    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        self._wrapped.setup(orchestrator)
        orchestrator.register_agent("procedure", self._on_procedure)

    def _on_procedure(self, event) -> None:
        tick = event.payload.get("tick", 0)
        target = event.payload.get("target", "unknown")
        procedure = event.payload.get("procedure", "")
        self._procedures.append({"tick": tick, "target": target})

        vitals = self._produce_vitals(tick, procedure)
        self._orchestrator.authority.execute_vitals_injection(tick, vitals)
        print(f"[LogicPatch:post_procedure_vitals] tick={tick} injected vitals after procedure for={target}")

    def _produce_vitals(self, tick: int, procedure_name: str = "") -> dict:
        ranges = {
            "heart_rate": (60, 100),
            "bp_systolic": (90, 140),
            "bp_diastolic": (60, 90),
            "spo2": (94, 100),
            "temperature": (36.1, 37.2),
        }
        config = getattr(self._orchestrator, 'config', None)
        if config:
            ranges = config.get_vital_ranges()
        return _directional_vitals(tick, procedure_name, ranges)


class EnforceRecoveryEvent:
    def __init__(self, wrapped_agent: ComplicationSignalAgent, recovery_window: int = 5):
        self._wrapped = wrapped_agent
        self._recovery_window = recovery_window
        self._procedures = []
        self._orchestrator = None

    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        self._wrapped.setup(orchestrator)
        orchestrator.register_agent("procedure", self._on_procedure)

    def _on_procedure(self, event) -> None:
        tick = event.payload.get("tick", 0)
        target = event.payload.get("target", "unknown")
        procedure = event.payload.get("procedure", "")
        self._procedures.append({"tick": tick, "target": target})

        config = getattr(self._orchestrator, 'config', None)
        window = self._recovery_window
        if config:
            window = config.get("procedures.yaml", "recovery_window", self._recovery_window)

        recovery_tick = tick + min(window, 1)
        vitals = self._produce_recovery_vitals(recovery_tick, target, procedure)
        self._orchestrator.authority.execute_vitals_injection(recovery_tick, vitals)
        self._orchestrator.authority.execute_recovery_event(recovery_tick, target)
        print(f"[LogicPatch:enforce_recovery] tick={recovery_tick} recovery event for={target}")

    def _produce_recovery_vitals(self, tick: int, target: str, procedure_name: str = "") -> dict:
        ranges = {
            "heart_rate": (60, 100),
            "bp_systolic": (90, 140),
            "bp_diastolic": (60, 90),
            "spo2": (94, 100),
            "temperature": (36.1, 37.2),
        }
        config = getattr(self._orchestrator, 'config', None)
        if config:
            ranges = config.get_vital_ranges()
        return _directional_vitals(tick, procedure_name, ranges)


class EnforceEventOrdering:
    def __init__(self, wrapped_agent):
        self._wrapped = wrapped_agent
        self._last_tick = -1
        self._orchestrator = None

    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        self._wrapped.setup(orchestrator)

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


LOGIC_PATCH_MAP = {
    "ensure_post_procedure_vitals": EnsurePostProcedureVitals,
    "enforce_recovery_event": EnforceRecoveryEvent,
    "enforce_event_ordering": EnforceEventOrdering,
}


def apply_logic_patches(procedure_agent, logic_patches: list):
    agent = procedure_agent
    for patch in logic_patches:
        handler_cls = LOGIC_PATCH_MAP.get(patch.action)
        if handler_cls is None:
            continue
        agent = handler_cls(agent)
    return agent
