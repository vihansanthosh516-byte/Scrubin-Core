import random
import hashlib
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AdversaryGenome:
    """Genome encoding adversarial strategy biases.

    Each bias is a float in [0, 1] representing probability weight for the
    corresponding fault type.
    """
    crash_bias: float
    delay_bias: float
    forge_bias: float
    equivocation_bias: float

    def mutate(self, seed: str) -> "AdversaryGenome":
        """Return a mutated copy of the genome.

        Deterministic mutation uses a seed derived from the provided ``seed``
        string.  Small Gaussian jitter is applied to each bias, clamped to the
        ``[0.0, 1.0]`` range.
        """
        rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))

        def jitter(val: float) -> float:
            # Apply uniform perturbation in [-0.1, 0.1]
            return max(0.0, min(1.0, val + rng.uniform(-0.1, 0.1)))

        return AdversaryGenome(
            crash_bias=jitter(self.crash_bias),
            delay_bias=jitter(self.delay_bias),
            forge_bias=jitter(self.forge_bias),
            equivocation_bias=jitter(self.equivocation_bias),
        )


class EvolutionaryAdversary:
    """P7‑B: evolves adversarial strategies over generations.

    The adversary maintains a population of ``AdversaryGenome`` objects.  Each
    generation is evaluated by a Lyapunov‑derived fitness score; the best genome
    is selected and mutated to form the next generation.
    """

    def __init__(self, base_genome: AdversaryGenome):
        self.population: List[AdversaryGenome] = [base_genome]
        self.generation: int = 0

    # ---------------------------------------------------------------------
    def evaluate_fitness(self, genome: AdversaryGenome, lyapunov_score: float) -> float:
        """Compute a fitness value for ``genome``.

        A higher absolute Lyapunov exponent (more chaotic) yields higher fitness.
        The genome's bias weights act as a scaling factor, encouraging genomes
        that weight the fault types that actually produce chaos.
        """
        weight = (
            genome.crash_bias
            + genome.delay_bias
            + genome.forge_bias
            + genome.equivocation_bias
        )
        return abs(lyapunov_score) * weight

    # ---------------------------------------------------------------------
    def select_best(self, fitness_map: Dict[int, float]) -> AdversaryGenome:
        """Select the genome with the highest fitness.

        ``fitness_map`` maps population indices to fitness values.
        """
        best_idx = max(fitness_map, key=fitness_map.get)
        return self.population[best_idx]

    # ---------------------------------------------------------------------
    def evolve(self, fitness_scores: List[float], trajectory_hash: str) -> None:
        """Perform one evolution step.

        * ``fitness_scores`` – list of Lyapunov‑derived scores, one per genome.
        * ``trajectory_hash`` – deterministic identifier for the current run.
        """
        # Compute fitness per individual
        fitness_map: Dict[int, float] = {
            i: self.evaluate_fitness(gen, fitness_scores[i])
            for i, gen in enumerate(self.population)
        }

        # Choose the best genome as parent
        parent = self.select_best(fitness_map)

        # Deterministic seed for this generation
        base_seed = f"{trajectory_hash}:{self.generation}"

        # Produce a new population (simple two‑offspring scheme)
        self.population = [
            parent.mutate(base_seed),
            parent.mutate(base_seed + "a"),
        ]
        self.generation += 1
