import time
from typing import Dict, List, Any
from collections import deque

class ClusterTelemetry:
    """
    Aggregates performance and health metrics across the distributed runtime.
    """
    def __init__(self):
        self.node_metrics: Dict[str, Dict[str, deque]] = {}
        self.global_throughput = deque(maxlen=100)

    def record_node_event(self, node_id: str, event_type: str, duration_ms: float):
        if node_id not in self.node_metrics:
            self.node_metrics[node_id] = {
                "latencies": deque(maxlen=100),
                "success_count": deque(maxlen=100)
            }
        
        self.node_metrics[node_id]["latencies"].append(duration_ms)
        self.global_throughput.append(time.time())

    def get_cluster_stats(self) -> Dict[str, Any]:
        return {
            "active_nodes": len(self.node_metrics),
            "avg_latency_ms": self._get_avg_latency(),
            "total_throughput": len(self.global_throughput)
        }

    def _get_avg_latency(self) -> float:
        total = 0.0
        count = 0
        for m in self.node_metrics.values():
            if m["latencies"]:
                total += sum(m["latencies"])
                count += len(m["latencies"])
        return total / count if count > 0 else 0.0
