from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid

@dataclass
class ExperimentConfig:
    id: str = field(default_factory=lambda: f"exp-{uuid.uuid4().hex[:8]}")
    name: str = "New Experiment"
    
    # Phase 12 Extensions
    phase12_mode: bool = True
    vectorized: bool = False
    distributed: bool = False
    latent_world_model: bool = False
    governance_enabled: bool = False
    
    policy_overrides: Dict[str, Any] = field(default_factory=dict)
    
    iterations: int = 1
    cohort_size: int = 1

@dataclass
class ExperimentResult:
    experiment_id: str
    status: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    session_ids: List[str] = field(default_factory=list)

class ExperimentTracker:
    """
    Orchestrates large-scale experiments across the Control Plane.
    """
    def __init__(self):
        self.experiments: Dict[str, ExperimentConfig] = {}
        self.results: Dict[str, ExperimentResult] = {}

    def run_experiment(self, config: ExperimentConfig) -> str:
        self.experiments[config.id] = config
        self.results[config.id] = ExperimentResult(experiment_id=config.id, status="STARTED")
        return config.id

    def log_result(self, experiment_id: str, metrics: Dict[str, Any], session_id: Optional[str] = None):
        if experiment_id in self.results:
            res = self.results[experiment_id]
            res.metrics.update(metrics)
            if session_id:
                res.session_ids.append(session_id)
