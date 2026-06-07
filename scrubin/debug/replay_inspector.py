# Replay inspector – deterministic tick‑by‑tick reconstruction.
"""
Provides a ``ReplayInspector`` class that, given a deterministic engine capable
of evolving a ``WorldState`` (or compatible state object), can replay a run
tick by tick and emit ``ReplayFrame`` objects that contain the tick, a stable hash
of the resulting state and a shallow diff from the previous state.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Any

# The deterministic world hash utility used across the codebase.
from scrubin.runtime.state_hashing import deterministic_world_hash


@dataclass(frozen=True)
class ReplayFrame:
    """Snapshot of a single tick during replay.

    Attributes
    ----------
    tick: int
        The simulation tick after the engine step.
    state_hash: str
        Deterministic SHA‑256 hash of the full world state.
    diff_from_previous: dict
        Shallow diff of top‑level fields compared to the prior tick. Empty for the
        first tick.
    """

    tick: int
    state_hash: str
    diff_from_previous: dict


class ReplayInspector:
    """Utility to deterministically replay a run.

    Parameters
    ----------
    engine: Any
        An object with a deterministic ``evolve(state) -> state`` method. The
        engine must not have side‑effects; state objects are expected to be
        immutable. The exact type is not enforced to keep the inspector generic.
    """

    def __init__(self, engine: Any):
        self.engine = engine

    @staticmethod
    def _hash_state(state: Any) -> str:
        """Return a deterministic hash for a world‑state‑like object.

        If the object is a ``WorldState`` we reuse the existing hash function;
        otherwise we fall back to a JSON‑based stable hash.
        """
        try:
            # ``deterministic_world_hash`` works for WorldState instances.
            return deterministic_world_hash(state)  # type: ignore[arg-type]
        except Exception:
            # Fallback for plain ``dict`` or other JSON‑serialisable objects.
            data = json.dumps(state, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def _shallow_diff(prev: Any, cur: Any) -> dict:
        """Compute a shallow field‑level diff between two state representations.

        The diff is a mapping of field names to the *new* value present in ``cur``
        when it differs from ``prev``. Nested structures are not recursively
        diffed – this keeps the operation cheap and deterministic.
        """
        prev_dict = asdict(prev) if hasattr(prev, "__dataclass_fields__") else prev
        cur_dict = asdict(cur) if hasattr(cur, "__dataclass_fields__") else cur
        diff: dict = {}
        for key, cur_val in cur_dict.items():
            if isinstance(prev_dict, dict):
                prev_val = prev_dict.get(key)
            else:
                prev_val = getattr(prev_dict, key, None)
            if cur_val != prev_val:
                diff[key] = cur_val
        return diff

    def replay(self, initial_state: Any, ticks: int) -> List[ReplayFrame]:
        """Replay ``ticks`` steps starting from ``initial_state``.

        Returns a list of ``ReplayFrame`` objects, one per tick. The first frame
        corresponds to the state after the first ``engine.evolve`` call.
        """
        frames: List[ReplayFrame] = []
        prev_state = initial_state
        for _ in range(ticks):
            # Deterministically evolve one tick.
            # Determine the correct evolution method – ``evolve`` for full engines or ``step`` for simple kernels.
            if hasattr(self.engine, "evolve"):
                new_state = self.engine.evolve(prev_state)
            elif hasattr(self.engine, "step"):
                new_state = self.engine.step(prev_state)
            else:
                raise AttributeError("Engine must have an 'evolve' or 'step' method")
            # Compute hash of the new state.
            state_hash = self._hash_state(new_state)
            # Compute shallow diff relative to previous state.
            diff = self._shallow_diff(prev_state, new_state)
            # Extract tick from the new state if possible; fall back to None.
            try:
                tick = getattr(new_state, "tick", None) if hasattr(new_state, "tick") else new_state.get("tick", None)  # type: ignore[arg-type]
            except Exception:
                tick = None
            frames.append(ReplayFrame(tick=tick, state_hash=state_hash, diff_from_previous=diff))
            prev_state = new_state
        return frames
