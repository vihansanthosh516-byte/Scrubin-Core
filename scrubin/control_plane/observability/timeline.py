from dataclasses import dataclass, field
from typing import List, Dict, Any
from scrubin.control_plane.streaming.event_stream import StreamEvent

@dataclass
class TimelineFrame:
    tick: int
    events: List[StreamEvent] = field(default_factory=list)
    vitals_snapshot: Dict[str, Any] = field(default_factory=dict)

class ExecutionTimeline:
    """
    Reconstructs a unified execution timeline from distributed events.
    """
    def __init__(self):
        self.frames: Dict[int, TimelineFrame] = {}

    def ingest_event(self, event: StreamEvent):
        tick = event.tick or 0
        if tick not in self.frames:
            self.frames[tick] = TimelineFrame(tick=tick)
        
        self.frames[tick].events.append(event)
        
        # If it's a vitals event, update the snapshot for this frame
        if event.topic == "patient.vitals":
            self.frames[tick].vitals_snapshot.update(event.payload)

    def get_ordered_timeline(self) -> List[TimelineFrame]:
        return [self.frames[t] for t in sorted(self.frames.keys())]
