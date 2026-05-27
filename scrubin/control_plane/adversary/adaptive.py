import hashlib
import random
from typing import Any, Dict, List

from .byzantine import ByzantineEvent, FaultType
from .byzantine import ByzantineAdversary  # Not used directly but kept for reference
from .byzantine import ByzantineEvent
from .byzantine import FaultType
from .byzantine import ByzantineEvent
from .byzantine import FaultType
from .byzantine import ByzantineEvent
from .byzantine import FaultType

from dataclasses import dataclass, field


@dataclass
class AdversaryMemory:
    """Tracks deterministic learning state for the adaptive adversary.

    The memory is serializable via its hash and influences policy selection.
    """

    # Cumulative impact score for each fault type (higher = more effective)
    impact_score: Dict[str, float] = field(default_factory=dict)
    # Simple list of applied fault types in order – useful for replay
    fault_history: List[str] = field(default_factory=list)

    def update(self, fault_type: str, impact: float) -> None:
        """Record the result of a fault.

        ``impact`` is a numeric signal (e.g., 0‑1) representing how damaging the
        fault was.  The score is decayed over time to allow recent events to have
        higher weight.
        """
        self.fault_history.append(fault_type)
        # Exponential moving average with decay factor 0.9
        self.impact_score[fault_type] = (
            self.impact_score.get(fault_type, 0.0) * 0.9 + impact
        )

    def best_fault(self) -> str:
        """Return the fault type with the highest impact score.

        If no data is present, fall back to ``crash`` as a generic fault.
        """
        if not self.impact_score:
            return FaultType.CRASH
        # max by value, resolve ties by deterministic order of keys
        return max(self.impact_score.items(), key=lambda kv: kv[1])[0]

    def hash(self) -> str:
        """Deterministic hash of the memory contents.

        Used as part of the RNG seed for the policy so that the same memory
        yields the same deterministic decisions.
        """
        s = f"{self.impact_score}:{self.fault_history}"
        return hashlib.sha256(s.encode()).hexdigest()


class AdaptiveAdversary:
    """P6.3: Learning‑based adversary built on the P6.2 fault model.

    The adversary retains a persistent ``AdversaryMemory`` that is updated
    according to a numeric ``feedback`` signal supplied by the kernel after each
    tick.  All decisions are deterministic because the RNG seeds are derived
    from the tick, world ``state_hash``, ``node_id`` and the current memory hash.
    """

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.memory = AdversaryMemory()

    # -----------------------------------------------------------------
    # Public entry point – deterministic injection of faults.
    # -----------------------------------------------------------------
    def inject(
        self,
        events: List[Dict[str, Any]],
        tick_id: int,
        state_hash: str,
        node_id: str = "node-0",
        feedback: float | None = None,
    ) -> List[ByzantineEvent]:
        """Inject faults into ``events`` based on learned policy.

        Parameters
        ----------
        events:
            List of event dictionaries.
        tick_id:
            Current simulation tick.
        state_hash:
            SHA‑256 hash of the world state for the tick.
        node_id:
            Identifier of the node producing the events.
        feedback:
            Optional numeric signal (0‑1) indicating the effectiveness of the
            previously injected fault. ``None`` means *no learning* for this
            invocation.
        """
        # -----------------------------------------------------------------
        # 1. Optional learning step – incorporate feedback from the previous tick.
        # -----------------------------------------------------------------
        if feedback is not None:
            # ``last_fault`` is the most recent fault we injected; if none yet we
            # assume a benign ``crash`` placeholder.
            last_fault = (
                self.memory.fault_history[-1]
                if self.memory.fault_history
                else FaultType.CRASH
            )
            self.memory.update(last_fault, feedback)

        # -----------------------------------------------------------------
        # 2. Choose a fault type via deterministic policy.
        # -----------------------------------------------------------------
        chosen_fault = self._policy(tick_id, state_hash)

        # -----------------------------------------------------------------
        # 3. Apply the chosen fault to each event using a deterministic RNG.
        # -----------------------------------------------------------------
        rng = self._make_rng(tick_id, state_hash, node_id)
        results: List[ByzantineEvent] = []
        for event in events:
            roll = rng.random()
            # The deterministic thresholds mirror the P6.2 probabilities but are
            # all gated by ``chosen_fault`` – only the selected fault type can be
            # applied.
            if chosen_fault == FaultType.CRASH and roll < 0.3:
                corrupted = {}
            elif chosen_fault == FaultType.DELAY and roll < 0.4:
                corrupted = {**event, "delayed": True}
            elif chosen_fault == FaultType.EQUIVOCATE and roll < 0.5:
                corrupted = {**event, "version": "ALT"}
            elif chosen_fault == FaultType.FORGE:
                corrupted = {**event, "forged": True}
            else:
                corrupted = event.copy()

            results.append(
                ByzantineEvent(
                    original=event,
                    corrupted=corrupted,
                    fault_type=chosen_fault,
                    node_id=node_id,
                    tick_id=tick_id,
                )
            )
        return results

    # -----------------------------------------------------------------
    # Deterministic policy selection.
    # -----------------------------------------------------------------
    def _policy(self, tick_id: int, state_hash: str) -> str:
        """Select a fault type based on learned impact scores.

        The policy is deterministic: it builds a seed from the tick, the world
        ``state_hash`` and the current memory hash, then uses a ``random.Random``
        instance to optionally explore alternative faults (20% chance).
        """
        base = self.memory.best_fault()
        # Build a reproducible seed incorporating memory state.
        seed_input = f"{tick_id}:{state_hash}:{self.memory.hash()}"
        seed = int(hashlib.sha256(seed_input.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        # Exploration – occasionally try a different fault.
        if rng.random() < 0.2:
            return rng.choice([FaultType.CRASH, FaultType.DELAY, FaultType.EQUIVOCATE, FaultType.FORGE])
        return base

    # -----------------------------------------------------------------
    # Helper to obtain a deterministic RNG for a given context.
    # -----------------------------------------------------------------
    def _make_rng(self, tick_id: int, state_hash: str, node_id: str) -> random.Random:
        seed_str = f"{self.seed}:{tick_id}:{state_hash}:{node_id}"
        seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
        return random.Random(seed)
