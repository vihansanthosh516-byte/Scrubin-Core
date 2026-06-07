'''Experiment manager – orchestrates creation, scheduling, and execution of deterministic experiments.'''
from __future__ import annotations

import itertools
import uuid
from typing import Dict, List, Tuple, Any

from scrubin.experiments.experiment_models import (
    ExperimentDefinition,
    ExperimentRun,
    ParameterSweep,
    ExperimentArtifact,
)
from scrubin.control_plane.p9_debug import DebugFacade
from scrubin.control_plane.kernel import ControlPlaneKernel


class ExperimentManager:
    '''Manage experiments and their deterministic execution runs.

    This manager is entirely in‑memory and does not mutate any simulation state.
    Runs are executed via the existing IsolationEngine (P.8) through the
    ControlPlaneKernel.
    '''

    def __init__(self, kernel: ControlPlaneKernel):
        self.kernel = kernel
        self.debug = DebugFacade(kernel)
        # Mapping experiment name -> definition
        self._definitions: Dict[str, ExperimentDefinition] = {}
        # Mapping experiment name -> list of ExperimentRun (immutable instances)
        self._runs: Dict[str, List[ExperimentRun]] = {}
        # Mapping run_id -> ExecutionArtifact (from P.8)
        self._artifacts: Dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Experiment lifecycle
    # ---------------------------------------------------------------------
    def create_experiment(self, definition: ExperimentDefinition) -> str:
        """Register a new experiment. Returns the experiment name (unique)."""
        if definition.name in self._definitions:
            raise ValueError(f"Experiment '{definition.name}' already exists")
        self._definitions[definition.name] = definition
        # Generate runs immediately (queued state)
        runs = self._generate_runs(definition)
        self._runs[definition.name] = runs
        return definition.name

    def list_experiments(self) -> List[str]:
        return sorted(self._definitions.keys())

    def get_definition(self, name: str) -> ExperimentDefinition:
        return self._definitions[name]

    # ---------------------------------------------------------------------
    # Run generation and scheduling
    # ---------------------------------------------------------------------
    def _generate_parameter_sweep(self, definition: ExperimentDefinition) -> ParameterSweep:
        """Deterministically create a Cartesian product of parameters.
        The resulting combos are sorted tuples of (name, value) for reproducibility.
        """
        if not definition.parameters:
            # No parameter grid – single empty combo.
            return ParameterSweep(combos=((),))
        # Ensure deterministic order: sort parameter names.
        sorted_names = sorted(definition.parameters.keys())
        value_lists = [definition.parameters[name] for name in sorted_names]
        combos = []
        for prod in itertools.product(*value_lists):
            combo = tuple(zip(sorted_names, prod))  # already sorted by name
            combos.append(combo)
        return ParameterSweep(combos=tuple(combos))

    def _generate_runs(self, definition: ExperimentDefinition) -> List[ExperimentRun]:
        """Create all runs for an experiment – initially queued.
        Each run combines a parameter combo with each seed.
        """
        param_sweep = self._generate_parameter_sweep(definition)
        runs: List[ExperimentRun] = []
        # Deterministic ordering: iterate seeds after parameters.
        for combo in param_sweep.combos:
            for seed in definition.seeds:
                # Generate deterministic run_id – hash of name+combo+seed.
                run_id = f"{definition.name}:{seed}:{hash(combo)}"  # simple deterministic string
                runs.append(
                    ExperimentRun(
                        run_id=run_id,
                        experiment_name=definition.name,
                        params=combo,
                        seed=seed,
                        status="queued",
                        artifact=None,
                    )
                )
        # Store in deterministic order: sort by (experiment name, params tuple, seed)
        runs.sort(key=lambda r: (r.experiment_name, r.params, r.seed))
        return runs

    def get_runs(self, name: str) -> List[ExperimentRun]:
        return list(self._runs.get(name, []))

    # ---------------------------------------------------------------------
    # Scheduling & execution
    # ---------------------------------------------------------------------
    def schedule_and_execute(self, name: str) -> None:
        """Execute all runs for an experiment in deterministic order.
        Updates the internal run records with status and artifacts.
        """
        runs = self._runs.get(name)
        if runs is None:
            raise ValueError(f"Experiment '{name}' not found")
        # Deterministic ordering already ensured by _generate_runs.
        updated_runs: List[ExperimentRun] = []
        for run in runs:
            # Update status to running.
            running_run = ExperimentRun(
                run_id=run.run_id,
                experiment_name=run.experiment_name,
                params=run.params,
                seed=run.seed,
                status="running",
                artifact=None,
            )
            updated_runs.append(running_run)
            # Build config merging definition config and parameters.
            definition = self._definitions[name]
            cfg: Dict[str, Any] = dict(definition.config)
            cfg.update({k: v for k, v in run.params})
            cfg.update({"ticks": definition.tick_count})
            # Execute via IsolationEngine through kernel.run_simulation.
            try:
                artifact = self.kernel.run_simulation({"ticks": definition.tick_count, "seed": run.seed, **cfg})
                # Store artifact
                self._artifacts[run.run_id] = artifact
                completed_run = ExperimentRun(
                    run_id=run.run_id,
                    experiment_name=run.experiment_name,
                    params=run.params,
                    seed=run.seed,
                    status="completed",
                    artifact=artifact,
                )
                updated_runs[-1] = completed_run
            except Exception as exc:
                failed_run = ExperimentRun(
                    run_id=run.run_id,
                    experiment_name=run.experiment_name,
                    params=run.params,
                    seed=run.seed,
                    status="failed",
                    artifact=None,
                )
                updated_runs[-1] = failed_run
        # Replace stored runs with updated list.
        self._runs[name] = updated_runs

    def get_artifact(self, run_id: str) -> Any:
        return self._artifacts.get(run_id)

    # ---------------------------------------------------------------------
    # Summary & statistics
    # ---------------------------------------------------------------------
    def summarize(self, name: str) -> Dict[str, Any]:
        """Return a deterministic summary dictionary for the experiment.
        Includes counts, completed/failed, mean/min/max tick counts.
        """
        runs = self._runs.get(name, [])
        total = len(runs)
        completed = [r for r in runs if r.status == "completed"]
        failed = [r for r in runs if r.status == "failed"]
        completed_cnt = len(completed)
        failed_cnt = len(failed)
        # Tick stats from artifacts.
        tick_counts = []
        for r in completed:
            artifact = self._artifacts.get(r.run_id)
            if artifact:
                tick_counts.append(getattr(artifact, "metadata", {}).get("ticks", 0))
        if tick_counts:
            mean_ticks = sum(tick_counts) / len(tick_counts)
            min_ticks = min(tick_counts)
            max_ticks = max(tick_counts)
        else:
            mean_ticks = 0.0
            min_ticks = 0
            max_ticks = 0
        summary = {
            "experiment_name": name,
            "total_runs": total,
            "completed_runs": completed_cnt,
            "failed_runs": failed_cnt,
            "mean_ticks": mean_ticks,
            "min_ticks": min_ticks,
            "max_ticks": max_ticks,
        }
        return summary
