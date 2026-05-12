import concurrent.futures
from typing import List, Any, Callable
import random


class RolloutWorker:
    """
    Executes a single simulation rollout with a deterministic seed.
    """
    def __init__(self, runner_fn: Callable):
        self.runner_fn = runner_fn

    def execute(self, task_params: dict) -> Any:
        seed = task_params.get("seed", random.randint(0, 1000000))
        # Ensure determinism within the worker
        random.seed(seed)
        return self.runner_fn(task_params)


class DistributedRuntime:
    """
    Coordinator for parallel rollout execution and tournament management.
    """
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def run_parallel_rollouts(self, runner_fn: Callable, tasks: List[dict]) -> List[Any]:
        results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(RolloutWorker(runner_fn).execute, task): task 
                for task in tasks
            }
            for future in concurrent.futures.as_completed(future_to_task):
                try:
                    results.append(future.result())
                except Exception as exc:
                    print(f"[DistributedRuntime] Task generated an exception: {exc}")
        return results

    def run_tournament(self, evaluator_fn: Callable, agent_configs: List[dict], scenario: Any) -> dict:
        """
        Distributes agent evaluations across workers.
        """
        tasks = [{"agent_config": cfg, "scenario": scenario} for cfg in agent_configs]
        results = self.run_parallel_rollouts(evaluator_fn, tasks)
        # Aggregate results
        leaderboard = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        return {"leaderboard": leaderboard}
