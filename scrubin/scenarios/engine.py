from typing import Any
from scrubin.scenarios.dsl import ScenarioConfig, ScenarioEvent, ScenarioTrigger


class ScenarioEngine:
    def __init__(self, config: ScenarioConfig, orchestrator: Any):
        self.config = config
        self.orchestrator = orchestrator
        self.executed_events = set()
        self.executed_triggers = set()

    def process_tick(self, tick: int):
        """
        Process events and triggers for the current tick.
        """
        # 1. Process temporal events
        for i, event in enumerate(self.config.events):
            if event.tick == tick and i not in self.executed_events:
                print(f"[ScenarioEngine] Tick {tick}: Executing event '{event.action}'")
                self._execute_action(event.action, event.params)
                self.executed_events.add(i)

        # 2. Process triggers
        for i, trigger in enumerate(self.config.triggers):
            if trigger.once and i in self.executed_triggers:
                continue
            
            if self._evaluate_condition(trigger.condition):
                print(f"[ScenarioEngine] Tick {tick}: Trigger fired! '{trigger.condition}' -> '{trigger.action}'")
                self._execute_action(trigger.action, trigger.params)
                if trigger.once:
                    self.executed_triggers.add(i)

    def _execute_action(self, action: str, params: dict):
        """
        Map DSL actions to Orchestrator/Authority calls.
        """
        if action == "hemorrhage":
            severity = params.get("severity", "moderate")
            self.orchestrator.force_complication("hemorrhage", severity=severity)
        elif action == "staff_reduction":
            amount = params.get("amount", 10)
            rm = self.orchestrator.world.resource_manager
            if "staff_bandwidth" in rm.resources:
                res = rm.resources["staff_bandwidth"]
                res.total_capacity = max(0, res.total_capacity - amount)
        elif action == "ventilator_failure":
            rm = self.orchestrator.world.resource_manager
            if "ventilators" in rm.resources:
                res = rm.resources["ventilators"]
                res.total_capacity = 0 # Full failure for now
        elif action == "vitals_patch":
            vitals = params.get("vitals", {})
            self.orchestrator.submit_vitals(self.orchestrator.tick_count, vitals)
        else:
            # Fallback: try to publish as a generic bus event
            self.orchestrator.bus.publish(action, params)

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate a DSL condition string against the current world state.
        For Phase 10, we support simple physiological comparisons.
        Example: "bp_systolic < 70"
        """
        vitals = self.orchestrator.world.physiology.vitals
        
        # Very simple parser for "key op value"
        parts = condition.split()
        if len(parts) == 3:
            key, op, val_str = parts
            if key in vitals:
                val = float(val_str)
                actual = vitals[key]
                if op == "<": return actual < val
                if op == ">": return actual > val
                if op == "<=": return actual <= val
                if op == ">=": return actual >= val
                if op == "==": return actual == val
        
        return False
