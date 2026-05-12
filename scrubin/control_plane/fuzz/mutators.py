import random
import copy
from typing import List, Dict, Any

class BaseMutator:
    def mutate(self, events: List[Any], seed: int) -> List[Any]:
        return events

class ShuffleMutator(BaseMutator):
    def mutate(self, events: List[Any], seed: int) -> List[Any]:
        random.seed(seed)
        shuffled = copy.copy(events)
        random.shuffle(shuffled)
        return shuffled

class DuplicateMutator(BaseMutator):
    def mutate(self, events: List[Any], seed: int) -> List[Any]:
        random.seed(seed)
        if not events: return events
        mutated = copy.copy(events)
        # Duplicate 10% of events
        to_dup = random.sample(events, max(1, len(events)//10))
        mutated.extend(to_dup)
        return mutated

class NoiseMutator(BaseMutator):
    def mutate(self, events: List[Any], seed: int) -> List[Any]:
        random.seed(seed)
        mutated = copy.deepcopy(events)
        for ev in mutated:
            if ev.topic == "patient.vitals":
                # Perturb vitals slightly
                if "hr" in ev.payload:
                    ev.payload["hr"] += random.randint(-2, 2)
                if "spo2" in ev.payload:
                    ev.payload["spo2"] += random.randint(-1, 1)
        return mutated

class DelayMutator(BaseMutator):
    def mutate(self, events: List[Any], seed: int) -> List[Any]:
        random.seed(seed)
        mutated = copy.deepcopy(events)
        # Delay parent events by moving them later in the stream (simulating latency)
        if len(mutated) < 2: return mutated
        idx = random.randint(0, len(mutated)-2)
        item = mutated.pop(idx)
        mutated.insert(idx + 1, item)
        return mutated
