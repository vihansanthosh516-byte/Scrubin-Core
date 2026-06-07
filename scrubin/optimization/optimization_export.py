'''Export utilities for deterministic optimization results (Phase P.14).'''
from __future__ import annotations

import json
import csv
import io

from .optimization_models import ParetoFront, ParetoPoint


def export_pareto_front(front: ParetoFront, fmt: str = "json") -> str:
    """Export a Pareto front to ``fmt``. Supported formats: ``"json"`` and ``"csv"``.

    * JSON – a list of point dictionaries.
    * CSV – columns: experiment_id, sorted parameter keys, then objective names.
    The ordering of points and columns is deterministic.
    """
    if fmt == "json":
        data = [_point_to_dict(p) for p in front.points]
        return json.dumps(data, sort_keys=True)
    if fmt == "csv":
        if not front.points:
            return ""
        # Determine parameter column order (alphabetical)
        param_names = sorted({k for p in front.points for k, _ in p.parameters})
        # Determine objective names (order from scores)
        score_names = [s.name for s in front.points[0].scores] if front.points else []
        headers = ["experiment_id"] + param_names + score_names
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for p in front.points:
            row = [p.experiment_id]
            param_dict = dict(p.parameters)
            row.extend([param_dict.get(name) for name in param_names])
            row.extend([s.score for s in p.scores])
            writer.writerow(row)
        return output.getvalue()
    raise ValueError(f"Unsupported export format: {fmt}")


def _point_to_dict(point: ParetoPoint) -> dict:
    return {
        "experiment_id": point.experiment_id,
        "parameters": {k: v for k, v in point.parameters},
        "scores": {s.name: s.score for s in point.scores},
    }
