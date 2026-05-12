from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List
import heapq

from scrubin.core.ledger import EventLedger


_PROTECTED_EVENT_TYPES = frozenset({"procedure", "state_transition"})


@dataclass(order=True)
class Event:
    sort_key: tuple = field(compare=True)
    type: str = field(compare=False)
    payload: Dict[str, Any] = field(default_factory=dict, compare=False)
    tick: int = field(default=0, compare=False)
    sequence_id: int = field(default=0, compare=False)
    priority: int = field(default=0, compare=False)


class EventBus:
    def __init__(self, ledger=None):
        self._queue: List[Event] = []
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._tick = 0
        self._sequence_id = 0
        self.ledger = ledger or EventLedger()
        self._authority_token = None

    def set_authority_token(self, token):
        self._authority_token = token

    def subscribe(self, event_type: str, handler: Callable[[Event], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event_type: str, payload: Dict[str, Any], priority: int = 0, parent_id=None, _authority_token=None):
        if event_type in _PROTECTED_EVENT_TYPES:
            if _authority_token is None or _authority_token is not self._authority_token:
                raise PermissionError(
                    f"EventBus: publishing '{event_type}' requires ActionAuthority token. "
                    f"Direct publishing of protected event types is forbidden."
                )
        seq = self._sequence_id
        self._sequence_id += 1
        sort_key = (-priority, self._tick, seq)
        event = Event(
            sort_key=sort_key,
            type=event_type,
            payload=payload,
            tick=self._tick,
            sequence_id=seq,
            priority=priority,
        )
        heapq.heappush(self._queue, event)
        self.ledger.log(
            event_type=event_type,
            payload=payload,
            tick=self._tick,
            parent_id=parent_id,
            sequence_id=seq,
        )

    def tick(self):
        self._tick += 1
        processed = 0
        while self._queue:
            event = heapq.heappop(self._queue)
            handlers = self._subscribers.get(event.type, [])
            for handler in handlers:
                handler(event)
            processed += 1
        return {
            "tick": self._tick,
            "events_processed": processed,
        }

    def status(self):
        return {
            "queued_events": len(self._queue),
            "subscribed_types": list(self._subscribers.keys()),
            "tick": self._tick,
        }
