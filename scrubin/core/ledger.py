from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class LoggedEvent:
    id: int
    sequence_id: int
    type: str
    payload: Dict[str, Any]
    tick: int
    parent_id: Optional[int] = None


class EventLedger:
    def __init__(self):
        self._events: List[LoggedEvent] = []
        self._counter = 0
        self._listeners = []

    def add_listener(self, listener):
        self._listeners.append(listener)

    def log(self, event_type: str, payload: Dict[str, Any], tick: int, parent_id: int = None, sequence_id: int = 0):
        event = LoggedEvent(
            id=self._counter,
            sequence_id=sequence_id,
            type=event_type,
            payload=payload,
            tick=tick,
            parent_id=parent_id,
        )
        self._events.append(event)
        self._counter += 1
        for listener in self._listeners:
            listener(event)
        return event.id

    def all(self):
        return self._events

    def by_tick(self, tick: int):
        return [e for e in self._events if e.tick == tick]

    def to_json(self):
        return json.dumps([asdict(e) for e in self._events], indent=2)
