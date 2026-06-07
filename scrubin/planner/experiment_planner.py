'''Top‑level deterministic experiment planner – Phase P.12.'''
from __future__ import annotations

import datetime
import hashlib
import json

from typing import Dict, Tuple, Any

from .planner_models import PlanningRequest, PlanningResult, PlannerMetadata
from .hypothesis_engine import HypothesisEngine
from .parameter_planner import ParameterPlanner
from .constraint_engine import ConstraintEngine

from scrubin.experiments.experiment_models import ExperimentDefinition


class ExperimentPlanner:
    """Orchestrates planning steps and produces a PlanningResult."""

    def __init__(self, kernel) -> None:
        self.kernel = kernel  # Unused for now – placeholder for future integration.

    def plan(self, request: PlanningRequest) -> PlanningResult:
        # 1. Generate hypotheses – deterministic.
        hypotheses = HypothesisEngine.generate(request)

        # 2. Generate parameter grid (deterministic).
        param_grid = ParameterPlanner.generate(request)

        # 3. Apply constraints – may adjust grid or provide combo count.
        param_grid, total_combos = ConstraintEngine.apply(request, param_grid)

        # 4. Build deterministic ExperimentDefinition.
        name_hash = hashlib.sha256(f"{request.objective}{request.seed}".encode()).hexdigest()[:8]
        exp_name = f"plan_{name_hash}"
        tick_count = request.metadata.get("tick_count", 100)
        definition = ExperimentDefinition(
            name=exp_name,
            seeds=(request.seed,),
            tick_count=tick_count,
            parameters=param_grid,
            metadata=request.metadata,
            initial_state=request.initial_state,
            config={},
        )

        # 5. Estimate run count – seeds * combos, capped by max_runs if set.
        estimated_runs = len(definition.seeds) * total_combos
        if request.max_runs and request.max_runs > 0:
            estimated_runs = min(estimated_runs, request.max_runs)

        # 6. Compute deterministic planning hash.
        hash_input = json.dumps({
            "objective": request.objective,
            "seed": request.seed,
            "parameters": {k: list(v) for k, v in param_grid.items()},
            "constraints": [c.type for c in request.constraints],
            "max_runs": request.max_runs,
            "metadata": request.metadata,
        }, sort_keys=True).encode()
        planning_hash = hashlib.sha256(hash_input).hexdigest()

        # 7. Assemble metadata.
        metadata_obj = PlannerMetadata(created_at=datetime.datetime.utcnow().isoformat())

        # 8. Parameter summary.
        param_summary = {k: len(v) for k, v in param_grid.items()}

        return PlanningResult(
            experiment_definition=definition,
            hypotheses=hypotheses,
            parameter_summary=param_summary,
            estimated_run_count=estimated_runs,
            planning_hash=planning_hash,
            metadata=metadata_obj,
        )
