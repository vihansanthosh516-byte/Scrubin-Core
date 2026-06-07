'''Deterministic experiment scheduler.

Orders runs across multiple experiments by experiment name, then parameter tuple,
then seed. This ensures reproducible execution order when a global schedule is
required.
'''\nfrom __future__ import annotations\n\nfrom typing import List, Tuple\n\nfrom .experiment_models import ExperimentRun\n\n\nclass ExperimentScheduler:\n    '''Scheduler that returns a deterministic list of runs to execute.'''
\n    @staticmethod
    def order_runs(runs_by_experiment: dict[str, List[ExperimentRun]]) -> List[ExperimentRun]:
        """Flatten and sort runs from multiple experiments.
\n        Parameters
        ----------
        runs_by_experiment: dict mapping experiment name to list of runs.
\n        Returns
        -------
        List[ExperimentRun]
            Deterministically ordered runs.
        """
        all_runs: List[ExperimentRun] = []
        for run_list in runs_by_experiment.values():
            all_runs.extend(run_list)
        # Sort by (experiment_name, params tuple, seed)
        all_runs.sort(key=lambda r: (r.experiment_name, r.params, r.seed))
        return all_runs
