from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionResult:
    executed: bool
    action_name: str
    reason: str
    decision: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)


class DecisionExecutor:
    def __init__(self, authority=None, min_weighted_delta: float = 10.0, duplicate_window: int = 3):
        self._authority = authority
        self._min_weighted_delta = min_weighted_delta
        self._duplicate_window = duplicate_window
        self._execution_log: list[ExecutionResult] = []

    def evaluate(self, validation_result, orchestrator=None) -> ExecutionResult:
        from scrubin.models.intents import ActionIntent
        import uuid

        authority = self._authority
        if authority is None and orchestrator is not None:
            authority = getattr(orchestrator, "authority", None)

        if authority is None:
            result = ExecutionResult(
                executed=False,
                action_name=getattr(validation_result, "decision_action", "unknown"),
                reason="no_authority_configured",
            )
            self._execution_log.append(result)
            return result

        action_name = getattr(validation_result, "decision_action", "unknown")
        can_execute = self.should_execute(validation_result)

        if not can_execute:
            result = ExecutionResult(
                executed=False,
                action_name=action_name,
                reason=self._rejection_reason(validation_result),
            )
            self._execution_log.append(result)
            return result

        intent = ActionIntent(
            id=f"intent-exec-{uuid.uuid4().hex[:8]}",
            type="procedure",
            name=action_name,
            target="",
            priority=0.0,
            confidence=0.0,
            source="executor",
            reasoning="delegated_to_authority",
        )
        exec_result = authority.execute(intent)

        result = ExecutionResult(
            executed=exec_result.executed,
            action_name=action_name,
            reason=exec_result.reason,
        )
        self._execution_log.append(result)
        return result

    def should_execute(self, validation_result, ledger=None) -> bool:
        if validation_result.verdict != "strong_improvement":
            return False
        if validation_result.confidence != "high":
            return False
        if validation_result.weighted_delta < self._min_weighted_delta:
            return False
        return True

    def _rejection_reason(self, validation_result) -> str:
        reasons = []
        if validation_result.verdict != "strong_improvement":
            reasons.append(f"verdict={validation_result.verdict} (need strong_improvement)")
        if validation_result.confidence != "high":
            reasons.append(f"confidence={validation_result.confidence} (need high)")
        if validation_result.weighted_delta < self._min_weighted_delta:
            reasons.append(f"weighted_delta={validation_result.weighted_delta:+.1f} < {self._min_weighted_delta}")
        return "; ".join(reasons) if reasons else "rejected"

    @property
    def execution_log(self) -> list[ExecutionResult]:
        return list(self._execution_log)

    def to_dict(self, result: ExecutionResult) -> dict:
        return {
            "executed": result.executed,
            "action": result.action_name,
            "reason": result.reason,
        }
