from typing import Dict

class DeterministicCluster:
    """
    Foundation of distributed scaling: Partitioned Determinism.
    Assigns workers unique but deterministic seeds based on a global root.
    """
    def __init__(self, base_seed: int):
        self.base_seed = base_seed
        self.worker_seeds: Dict[int, int] = {}

    def assign_worker_seed(self, worker_id: int) -> int:
        """
        Derives a worker-specific seed from the global root.
        Ensures identical clusters produce identical results.
        """
        # Deterministic hashing of (base_seed, worker_id)
        seed = hash((self.base_seed, worker_id))
        self.worker_seeds[worker_id] = seed
        return seed
