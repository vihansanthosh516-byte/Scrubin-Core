import time
from typing import Dict, Any, List
from collections import deque
from scrubin.control_plane.streaming.event_stream import StreamEvent

class LiveMetricsAggregator:
    """
    Continuous live metrics aggregation from the simulation event stream.
    """
    def __init__(self):
        self.decisions_count = 0
        self.vitals_updates = 0
        self.start_time = time.time()
        self.mortality_rate = deque(maxlen=100)

    def process_event(self, event: StreamEvent):
        if event.topic == "planner.mcts_trace":
            self.decisions_count += 1
        elif event.topic == "patient.vitals":
            self.vitals_updates += 1
        elif event.topic == "clinical.mortality":
            self.mortality_rate.append(1)

    def get_live_throughput(self) -> Dict[str, float]:
        elapsed = time.time() - self.start_time
        return {
            "decisions_per_sec": self.decisions_count / elapsed if elapsed > 0 else 0,
            "vitals_updates_per_sec": self.vitals_updates / elapsed if elapsed > 0 else 0,
            "mortality_cumulative": sum(self.mortality_rate)
        }
