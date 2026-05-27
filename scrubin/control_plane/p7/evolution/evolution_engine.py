from typing import List


class EvolutionEngine:
    """Coordinates adversary evolution across simulation runs.

    The engine holds a reference to an ``EvolutionaryAdversary`` and invokes its
    ``evolve`` method after each run, passing the Lyapunov‑derived fitness scores
    and a deterministic hash of the trajectory.
    """

    def __init__(self, adversary):
        self.adversary = adversary

    def step(self, fitness_scores: List[float], trajectory_hash: str):
        """Advance one evolutionary step.

        Returns the new population of genomes.
        """
        self.adversary.evolve(fitness_scores, trajectory_hash)
        return self.adversary.population
