import time
from typing import Dict, List, Any
from collections import deque

class MetricsEngine:
    """
    Tracks control plane health, scheduler efficiency, and job performance.
    """
    def __init__(self, window_size: int = 100):
        self.job_latencies: Dict[str, deque] = {}
        self.throughput_counts = deque(maxlen=60) # Last 60 seconds
        self.saturation_level = 0.0
        self.window_size = window_size
        self.experiment_success_rate = 1.0

    def record_job_completion(self, job_type: str, duration_ms: float):
        if job_type not in self.job_latencies:
            self.job_latencies[job_type] = deque(maxlen=self.window_size)
        self.job_latencies[job_type].append(duration_ms)
        self.throughput_counts.append(time.time())

    def update_saturation(self, pending_count: int, running_count: int):
        # Simple heuristic: Pending / (Running + 1)
        self.saturation_level = pending_count / max(1, running_count)

    def get_health_report(self) -> Dict[str, Any]:
        report = {
            "status": "HEALTHY" if self.saturation_level < 5.0 else "DEGRADED",
            "saturation": self.saturation_level,
            "avg_latency": {},
            "throughput_jobs_per_min": len(self.throughput_counts)
        }
        
        for j_type, latencies in self.job_latencies.items():
            if latencies:
                report["avg_latency"][j_type] = sum(latencies) / len(latencies)
                
        return report

    def record_batch_efficiency(self, batch_size: int, saved_time_ms: float):
        # Tracks how much time is saved by vectorized batching
        pass
