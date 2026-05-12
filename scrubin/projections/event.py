from scrubin.projections.base import Projection
from scrubin.api.mappers import map_logged_event_to_dto

class EventProjection(Projection):
    def __init__(self, max_history=10000):
        self._events = []
        self._max_history = max_history

    def apply(self, event):
        origin = "authority" if event.type in ("procedure", "state_transition") else "engine"
        source = event.payload.get("source", "")
        intent_id = event.payload.get("intent_id", "")
        dto = map_logged_event_to_dto(
            event, origin=origin, source=source, intent_id=intent_id,
        )
        self._events.append(dto.to_dict())
        if len(self._events) > self._max_history:
            self._events.pop(0)

    def events_after(self, sequence_id: int):
        # sequence is event.id which is monotonically increasing
        return [e for e in self._events if e["sequence"] > sequence_id]

    def latest_sequence(self) -> int:
        return self._events[-1]["sequence"] if self._events else -1

    def get_recent(self, limit: int = 20):
        return self._events[-limit:]
