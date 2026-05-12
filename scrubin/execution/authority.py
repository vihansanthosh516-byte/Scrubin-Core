from dataclasses import dataclass, field

from scrubin.models.intents import ActionIntent


@dataclass
class ExecutionEvent:
    intent_id: str
    action_name: str
    outcome: str
    tick: int
    reason: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionResult:
    executed: bool
    intent_id: str
    action_name: str
    reason: str
    tick: int
    intent: ActionIntent | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "executed": self.executed,
            "intent_id": self.intent_id,
            "action_name": self.action_name,
            "reason": self.reason,
            "tick": self.tick,
        }


class ActionAuthority:
    def __init__(self, bus, ledger, state=None, duplicate_window: int = 3):
        self._bus = bus
        self._ledger = ledger
        self._state = state
        self._duplicate_window = duplicate_window
        self._execution_log: list[ExecutionEvent] = []
        self._authority_token = object()

    @property
    def authority_token(self):
        return self._authority_token

    @property
    def execution_log(self) -> list[ExecutionEvent]:
        return list(self._execution_log)

    def execute(self, intent: ActionIntent) -> ExecutionResult:
        if not isinstance(intent, ActionIntent):
            return ExecutionResult(
                executed=False,
                intent_id="",
                action_name="",
                reason=f"invalid intent type: {type(intent)}",
                tick=self._current_tick(),
            )

        if not self._is_well_formed(intent):
            return ExecutionResult(
                executed=False,
                intent_id=intent.id,
                action_name=intent.name,
                reason="intent_not_well_formed",
                tick=self._current_tick(),
                intent=intent,
            )

        if intent.type != "procedure":
            return ExecutionResult(
                executed=False,
                intent_id=intent.id,
                action_name=intent.name,
                reason=f"non-procedure intent type: {intent.type}",
                tick=self._current_tick(),
                intent=intent,
            )

        if self._is_duplicate(intent.name):
            reason = f"duplicate {intent.name} within {self._duplicate_window} ticks"
            ee = ExecutionEvent(
                intent_id=intent.id,
                action_name=intent.name,
                outcome="rejected",
                tick=self._current_tick(),
                reason=reason,
            )
            self._execution_log.append(ee)
            return ExecutionResult(
                executed=False,
                intent_id=intent.id,
                action_name=intent.name,
                reason=reason,
                tick=self._current_tick(),
                intent=intent,
            )

        tick = self._current_tick()

        self._bus.publish(
            "procedure",
            {
                "tick": tick,
                "procedure": intent.name,
                "target": intent.target or "",
            },
            _authority_token=self._authority_token,
        )

        self._ledger.log(
            "decision_execution",
            {
                "executed": True,
                "action": intent.name,
                "target": intent.target or "",
                "tick": tick,
                "source": intent.source,
                "intent_id": intent.id,
                "confidence": intent.confidence,
            },
            tick=tick,
        )

        ee = ExecutionEvent(
            intent_id=intent.id,
            action_name=intent.name,
            outcome="executed",
            tick=tick,
        )
        self._execution_log.append(ee)

        print(f"[ActionAuthority] tick={tick} procedure={intent.name} target={intent.target} (executed)")

        return ExecutionResult(
            executed=True,
            intent_id=intent.id,
            action_name=intent.name,
            reason="executed_by_authority",
            tick=tick,
            intent=intent,
        )

    def execute_vitals_injection(self, tick: int, vitals: dict, source: str = "logic_patch") -> dict:
        self._bus.publish(
            "vitals_update",
            {"tick": tick, "vitals": vitals},
            _authority_token=self._authority_token,
        )
        return {"vitals_injected": True, "tick": tick}

    def execute_recovery_event(self, tick: int, target: str, status: str = "monitoring") -> dict:
        self._bus.publish(
            "recovery",
            {"tick": tick, "target": target, "status": status},
        )
        return {"recovery_event": True, "tick": tick, "target": target}

    def _is_well_formed(self, intent: ActionIntent) -> bool:
        if not intent.id:
            return False
        if not intent.type:
            return False
        if not intent.name:
            return False
        return True

    def _is_duplicate(self, action_name: str) -> bool:
        current_tick = self._current_tick()
        for e in reversed(self._execution_log):
            if e.outcome != "executed":
                continue
            if e.action_name == action_name:
                if current_tick - e.tick < self._duplicate_window:
                    return True
        return False

    def _current_tick(self) -> int:
        if self._state is not None:
            if hasattr(self._state, 'tick_count'):
                return self._state.tick_count
            if hasattr(self._state, 'state') and hasattr(self._state.state, 'tick'):
                return self._state.state.tick
            if hasattr(self._state, 'tick'):
                return self._state.tick
        current = 0
        for e in self._ledger.all():
            if e.tick > current:
                current = e.tick
        return current
