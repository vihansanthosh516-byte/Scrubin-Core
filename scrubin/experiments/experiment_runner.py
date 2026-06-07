'''Runner for a single deterministic experiment run.'''
from __future__ import annotations

from typing import Dict, Any

from scrubin.control_plane.kernel import ControlPlaneKernel


class ExperimentRunner:
    '''Executes a single run via the existing IsolationEngine (P.8).'''

    def __init__(self, kernel: ControlPlaneKernel):
        self.kernel = kernel

    def run(self, ticks: int, seed: int, config: Dict[str, Any] | None = None) -> Any:
        """Execute an isolated simulation run.
        Returns the ``ExecutionArtifact`` produced by the kernel.
        """
        cfg = {"ticks": ticks, "seed": seed}
        if config:
            cfg.update(config)
        return self.kernel.run_simulation(cfg)
