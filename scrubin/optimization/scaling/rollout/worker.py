from typing import Any, List, Tuple

class RolloutWorker:
    """
    Stateless execution unit for clinical RL rollouts.
    Strictly follows seed-driven determinism.
    """
    def __init__(self, env_factory: Any, worker_id: int):
        self.env_factory = env_factory
        self.worker_id = worker_id
        self.env = None
        self.seed = 0

    def run_episode(self, policy: Any, seed: int) -> List[Tuple[Any, Any, float]]:
        """
        Executes a single deterministic episode trace.
        """
        self.seed = seed
        self.env = self.env_factory(seed)
        
        obs = self.env.reset()
        trace = []
        done = False
        
        while not done:
            # Policy must be deterministic for the given seed
            action = policy.act(obs, seed=self.seed)
            obs, reward, done, info = self.env.step(action)
            
            trace.append((obs, action, reward))
            
        return trace
