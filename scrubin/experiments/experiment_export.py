'''Export utilities for deterministic experiment results.'''
from __future__ import annotations

import csv
import json
from io import StringIO
from typing import List, Dict, Any

from .experiment_models import ExperimentDefinition, ExperimentRun, ExperimentArtifact


def export_experiment_to_json(definition: ExperimentDefinition, runs: List[ExperimentRun]) -> str:
    """Export an experiment definition and its runs to a JSON string.
    The output is deterministic: runs are ordered by (params, seed).
    """
    data = {
        "definition": {
            "name": definition.name,
            "seeds": list(definition.seeds),
            "tick_count": definition.tick_count,
            "parameters": {k: list(v) for k, v in definition.parameters.items()},
            "metadata": definition.metadata,
            "initial_state": definition.initial_state,
            "config": definition.config,
        },
        "runs": [
            {
                "run_id": run.run_id,
                "params": {k: v for k, v in run.params},
                "seed": run.seed,
                "status": run.status,
            }
            for run in runs
        ],
    }
    # Ensure deterministic ordering using sort_keys.
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def export_experiment_to_csv(definition: ExperimentDefinition, runs: List[ExperimentRun]) -> str:
    """Export experiment runs to a CSV string.
    Columns: run_id, seed, status, param_<name> for each parameter.
    Deterministic ordering of rows and columns.
    """
    param_names = sorted(definition.parameters.keys())
    fieldnames = ["run_id", "seed", "status"] + [f"param_{p}" for p in param_names]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for run in runs:
        row = {"run_id": run.run_id, "seed": run.seed, "status": run.status}
        param_dict = {k: v for k, v in run.params}
        for p in param_names:
            row[f"param_{p}"] = param_dict.get(p)
        writer.writerow(row)
    return output.getvalue()
