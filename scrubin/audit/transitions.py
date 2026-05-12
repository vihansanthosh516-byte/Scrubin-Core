from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StateTransition:
    tick: int
    source_event: str
    affected_system: str
    before: dict
    after: dict
    delta: dict


class TransitionAuditor:
    def __init__(self, ledger=None):
        self._transitions: List[StateTransition] = []
        self._ledger = ledger

    def record(
        self,
        tick: int,
        source_event: str,
        affected_system: str,
        before: dict,
        after: dict,
    ) -> StateTransition:
        delta = _compute_delta(before, after)
        transition = StateTransition(
            tick=tick,
            source_event=source_event,
            affected_system=affected_system,
            before=before,
            after=after,
            delta=delta,
        )
        self._transitions.append(transition)
        if self._ledger is not None:
            self._ledger.log(
                "state_transition_audit",
                {
                    "tick": tick,
                    "source_event": source_event,
                    "affected_system": affected_system,
                    "delta": delta,
                },
                tick=tick,
            )
        return transition

    def transitions_for_tick(self, tick: int) -> List[StateTransition]:
        return [t for t in self._transitions if t.tick == tick]

    def transitions_for_system(self, system: str) -> List[StateTransition]:
        return [t for t in self._transitions if t.affected_system == system]

    def all_transitions(self) -> List[StateTransition]:
        return list(self._transitions)

    @property
    def count(self) -> int:
        return len(self._transitions)

    def clear(self):
        self._transitions.clear()


def _compute_delta(before: dict, after: dict) -> dict:
    delta = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        b = before.get(key)
        a = after.get(key)
        if b != a:
            delta[key] = {"before": b, "after": a}
    return delta
