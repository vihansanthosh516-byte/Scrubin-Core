'''Export utilities for deterministic planner results.'''
from __future__ import annotations

import csv
import json
import itertools
from io import StringIO

from .planner_models import PlanningRequest, PlanningResult
from .parameter_planner import ParameterPlanner


def export_planning_request_to_json(request: PlanningRequest) -> str:
    """Export a PlanningRequest to a deterministic JSON string."""
    data = {
        "objective": request.objective,
        "seed": request.seed,
        "initial_state": request.initial_state,
        "constraints": [
            {
                "type": c.type,
                "parameters": {k: v for k, v in c.parameters},
            }
            for c in request.constraints
        ],
        "max_runs": request.max_runs,
        "metadata": request.metadata,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def export_planning_result_to_json(result: PlanningResult) -> str:
    """Export a PlanningResult to a deterministic JSON string."""
    exp = result.experiment_definition
    data = {
        "planning_hash": result.planning_hash,
        "experiment_definition": {
            "name": exp.name,
            "seeds": list(exp.seeds),
            "tick_count": exp.tick_count,
            "parameters": {k: list(v) for k, v in exp.parameters.items()},
            "metadata": exp.metadata,
            "initial_state": exp.initial_state,
            "config": exp.config,
        },
        "hypotheses": [h.description for h in result.hypotheses],
        "parameter_summary": result.parameter_summary,
        "estimated_run_count": result.estimated_run_count,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def export_parameter_grid_to_csv(request: PlanningRequest) -> str:
    """Export the deterministic parameter grid to CSV.
    Columns are the sorted parameter names and each row is a combination.
    """
    param_grid = ParameterPlanner.generate(request)
    param_names = sorted(param_grid.keys())
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=param_names)
    writer.writeheader()
    for combo in itertools.product(*(param_grid[name] for name in param_names)):
        row = {name: value for name, value in zip(param_names, combo)}
        writer.writerow(row)
    return output.getvalue()
