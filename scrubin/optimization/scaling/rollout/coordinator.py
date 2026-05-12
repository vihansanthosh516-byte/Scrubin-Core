from typing import List, Any
from scrubin.optimization.scaling.distributed.deterministic_cluster import DeterministicCluster

class RolloutCoordinator:
    """
    Global orchestrator for deterministic distributed rollouts.
    Dispatches policies to partitioned workers.
    """
    def __init__(self, cluster: DeterministicCluster, workers: List[Any]):
        self.cluster = cluster
        self.workers = workers

    def dispatch(self, policy: Any) -> List[List[Any]]:
        """
        Synchronous dispatch of rollout tasks across the worker pool.
        """
        results = []
        for i, worker in enumerate(self.workers):
            # Deterministically assign seeds per worker
            seed = self.cluster.assign_worker_seed(i)
            results.append(worker.run_episode(policy, seed=seed))
            
        return results
