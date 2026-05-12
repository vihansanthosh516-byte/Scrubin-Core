import random
from typing import List, Any
from scrubin.control_plane.fuzz.mutators import ShuffleMutator, DuplicateMutator, NoiseMutator, DelayMutator

class ChaosGenerator:
    """
    Generates structurally valid but semantically adversarial execution traces.
    """
    def __init__(self):
        self.mutators = [
            ShuffleMutator(),
            DuplicateMutator(),
            NoiseMutator(),
            DelayMutator()
        ]

    def generate_fuzz(self, events: List[Any], seed: int) -> List[Any]:
        random.seed(seed)
        fuzzed = events
        # Apply a random subset of mutators
        selected = random.sample(self.mutators, random.randint(1, len(self.mutators)))
        for m in selected:
            fuzzed = m.mutate(fuzzed, seed)
        return fuzzed
