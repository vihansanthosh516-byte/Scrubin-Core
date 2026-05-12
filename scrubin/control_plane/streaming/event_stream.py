import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from collections import deque

@dataclass
class StreamEvent:
    topic: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    tick: Optional[int] = None
    session_id: Optional[str] = None

class EventStream:
    """
    Global streaming event bus for ScrubIn operational observability.
    """
    def __init__(self, max_history: int = 10000):
        self._history = deque(maxlen=max_history)
        self._subscribers: Dict[str, List[Callable]] = {}

    def publish(self, topic: str, payload: Dict[str, Any], tick: Optional[int] = None, session_id: Optional[str] = None):
        event = StreamEvent(topic=topic, payload=payload, tick=tick, session_id=session_id)
        self._history.append(event)
        
        # Notify subscribers
        for pattern, callbacks in self._subscribers.items():
            if pattern == "*" or pattern == topic:
                for cb in callbacks:
                    cb(event)

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)

    def replay(self, topic: Optional[str] = None, since_tick: int = 0) -> List[StreamEvent]:
        return [e for e in self._history if (not topic or e.topic == topic) and (e.tick or 0) >= since_tick]
