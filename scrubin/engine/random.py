from __future__ import annotations

"""Deterministic random number streams for the procedural cognition engine.

Each logical subsystem receives its own ``random.Random`` instance seeded from the
base seed.  Adding a new stream does **not** affect the output of existing
streams – this guarantees replay invariance across subsystem boundaries.
"""

import random
from typing import Any


class SimulationRNG:
    """Container for deterministic RNG streams.

    Parameters
    ----------
    seed: int
        Base seed for the simulation.  Sub‑streams are derived by adding fixed
        offsets; the offsets are chosen arbitrarily but remain constant.
    """

    def __init__(self, seed: int = 0) -> None:
        # Offsets are spaced by 1 000 to reduce accidental overlap.
        self.base_seed = seed
        self.physiology = random.Random(seed + 1000)
        self.complications = random.Random(seed + 2000)
        self.hidden_effects = random.Random(seed + 3000)
        self.option_generation = random.Random(seed + 4000)

    # Convenience wrappers – delegate to the appropriate sub‑stream.
    # Users can also access the streams directly via the attributes above.
    def random(self) -> float:
        """Return a float in the ``[0.0, 1.0)`` range using the physiology stream.
        """
        return self.physiology.random()

    def randint(self, a: int, b: int) -> int:
        return self.physiology.randint(a, b)

    def choice(self, seq: list[Any]) -> Any:
        return self.physiology.choice(seq)
