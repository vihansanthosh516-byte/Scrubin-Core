from typing import List, Any
import random

class MutationComposer:
    """
    Builds complex mutation pipelines by layering and composing pure mutators.
    """
    def __init__(self, mutators: List[Any]):
        self.mutators = mutators

    def compose_layers(self, events: List[Any], depth: int, seed: int) -> List[Any]:
        """
        Recursively applies layers of mutations to the event stream.
        """
        random.seed(seed)
        fuzzed = events
        
        for layer in range(depth):
            # Pick a subset of mutators for this layer
            subset = random.sample(self.mutators, random.randint(1, len(self.mutators)))
            for mutator in subset:
                fuzzed = mutator.mutate(fuzzed, seed + layer)
                
        return fuzzed
