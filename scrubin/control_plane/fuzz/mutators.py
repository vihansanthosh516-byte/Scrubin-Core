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
        """Perturb patient vitals events.

        Supports both ``SemanticEvent`` objects (with ``topic`` attribute) and
        plain dictionaries that contain a ``"topic"`` key.  The mutation is
        deliberately nondeterministic across different ``seed`` values, but
        deterministic when the same seed is used.
        """
        random.seed(seed)
        mutated = copy.deepcopy(events)
        for ev in mutated:
            # Determine topic (attribute or dict key)
            topic = getattr(ev, "topic", None)
+            if topic is None and isinstance(ev, dict):
+                topic = ev.get("topic")
+            if topic != "patient.vitals":
+                continue
+            # Access payload (attribute or dict key)
+            payload = getattr(ev, "payload", None)
+            if payload is None and isinstance(ev, dict):
+                payload = ev.get("payload", {})
+            if not isinstance(payload, dict):
+                continue
+            # Apply perturbations
+            if "hr" in payload:
+                payload["hr"] = payload.get("hr", 0) + random.randint(-2, 2)
+            if "spo2" in payload:
+                payload["spo2"] = payload.get("spo2", 0) + random.randint(-1, 1)
+            # If ev is a dict, write back mutated payload
+            if isinstance(ev, dict):
+                ev["payload"] = payload
+            else:
+                # For frozen dataclasses this would be a mutation error; however
+                # ``SemanticEvent`` is frozen, so we cannot modify it in‑place.
+                # Instead we replace the object with a shallow copy that has the
+                # updated payload using ``replace`` from ``dataclasses``.
+                from dataclasses import replace
+                ev = replace(ev, payload=payload)
+        return mutated

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
