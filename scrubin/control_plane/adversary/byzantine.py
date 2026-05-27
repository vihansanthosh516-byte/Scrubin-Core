import copy
import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any, Dict, List


class FaultType:
    """Enum‑like container for fault type identifiers."""

    CRASH = "crash"
    DELAY = "delay"
    EQUIVOCATE = "equivocate"
    FORGE = "forge"
    NONE = "none"


@dataclass(frozen=True)
class ByzantineEvent:
    """Container describing a single injected fault.

    Attributes
    ----------
    original: Dict[str, Any]
        The event before corruption.
    corrupted: Dict[str, Any]
        The event after applying the fault (may be empty for a crash).
    fault_type: str
        One of :class:`FaultType` values.
    node_id: str
        Identifier of the node on which the fault was applied.
    tick_id: int
        Simulation tick at which the fault was introduced.
    """

    original: Dict[str, Any]
    corrupted: Dict[str, Any]
    fault_type: str
    node_id: str
    tick_id: int


class ByzantineAdversary:
    """Deterministic Byzantine fault injector (P6.2).

    The adversary is a pure function of ``(seed, tick_id, state_hash, node_id)``.
    Given the same inputs it will always return the same list of
    :class:`ByzantineEvent` objects.
    """

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def inject(
        self,
        events: List[Dict[str, Any]],
        tick_id: int,
        state_hash: str,
        node_id: str = "node-0",
    ) -> List[ByzantineEvent]:
        """Inject faults into ``events``.

        Parameters
        ----------
        events:
            List of event dictionaries – the adversary never mutates the
            original list.
        tick_id:
            Current simulation tick.
        state_hash:
            SHA‑256 hash (hex string) of the world state at ``tick_id``.
        node_id:
            Identifier of the node whose output we are corrupting.

        Returns
        -------
        List[ByzantineEvent]
            One result per input event, preserving order.
        """
        # Deterministic RNG based on all inputs – no global randomness.
        rng = self._make_rng(tick_id, state_hash, node_id)

        corrupted_events: List[ByzantineEvent] = []
        for event in events:
            # Defensive copy – we do not want to mutate caller data.
            original = copy.deepcopy(event)
            roll = rng.random()

            # Probability bands – feel free to tune. They are deliberately
            # deterministic because they depend on ``rng``.
            if roll < 0.20:
                corrupted = self._crash(original, tick_id, node_id)
            elif roll < 0.40:
                corrupted = self._delay(original, tick_id, node_id, rng)
            elif roll < 0.60:
                corrupted = self._equivocate(original, tick_id, node_id, rng)
            elif roll < 0.75:
                corrupted = self._forge(original, tick_id, node_id)
            else:
                corrupted = ByzantineEvent(
                    original=original,
                    corrupted=original.copy(),
                    fault_type=FaultType.NONE,
                    node_id=node_id,
                    tick_id=tick_id,
                )
            corrupted_events.append(corrupted)
        return corrupted_events

    # ---------------------------------------------------------------------
    # Fault implementations (private helpers)
    # ---------------------------------------------------------------------
    def _crash(self, event: Dict[str, Any], tick_id: int, node_id: str) -> ByzantineEvent:
        """Simulate a silent drop – the corrupted payload is empty."""
        return ByzantineEvent(
            original=event,
            corrupted={},  # Dropped event – no data.
            fault_type=FaultType.CRASH,
            node_id=node_id,
            tick_id=tick_id,
        )

    def _delay(
        self,
        event: Dict[str, Any],
        tick_id: int,
        node_id: str,
        rng: random.Random,
    ) -> ByzantineEvent:
        """Add a deterministic ``delayed`` flag.

        ``rng`` is passed so that the decision to delay can be made
        deterministically (future extensions may use it for variable delays).
        """
        corrupted = event.copy()
        # Deterministic flag – always true for a delay fault.
        corrupted["delayed"] = True
        # Optionally add a synthetic delay amount derived from ``rng``.
        # We keep it simple: a small integer between 1‑5.
        corrupted["delay_ticks"] = rng.randint(1, 5)
        return ByzantineEvent(
            original=event,
            corrupted=corrupted,
            fault_type=FaultType.DELAY,
            node_id=node_id,
            tick_id=tick_id,
        )

    def _equivocate(
        self,
        event: Dict[str, Any],
        tick_id: int,
        node_id: str,
        rng: random.Random,
    ) -> ByzantineEvent:
        """Produce two mutually exclusive variants and pick one.

        The choice is deterministic because ``rng`` is seeded.
        """
        variant_a = event.copy()
        variant_b = event.copy()
        variant_a["version"] = "A"
        variant_b["version"] = "B"
        # Deterministic selection – ``rng`` decides which variant is emitted.
        chosen = rng.choice([variant_a, variant_b])
        return ByzantineEvent(
            original=event,
            corrupted=chosen,
            fault_type=FaultType.EQUIVOCATE,
            node_id=node_id,
            tick_id=tick_id,
        )

    def _forge(self, event: Dict[str, Any], tick_id: int, node_id: str) -> ByzantineEvent:
        """Create a synthetically valid but forged event.

        The ``signature`` field is a short hash of the original payload – this
        guarantees reproducibility without revealing the full payload.
        """
        corrupted = event.copy()
        corrupted["forged"] = True
        # Use a stable, JSON‑sorted representation for reproducible hashing.
        payload_repr = json.dumps(event, sort_keys=True)
        corrupted["signature"] = hashlib.sha256(payload_repr.encode()).hexdigest()[:8]
        return ByzantineEvent(
            original=event,
            corrupted=corrupted,
            fault_type=FaultType.FORGE,
            node_id=node_id,
            tick_id=tick_id,
        )

    # ---------------------------------------------------------------------
    # Deterministic RNG construction
    # ---------------------------------------------------------------------
    def _make_rng(self, tick_id: int, state_hash: str, node_id: str) -> random.Random:
        """Create a ``random.Random`` instance seeded from all context info.

        The seed string combines the user‑provided ``self.seed`` with the
        simulation tick, the world ``state_hash`` and the ``node_id``.  The result
        is fed through SHA‑256 and converted to an integer – this yields a 256‑bit
        deterministic seed that works across platforms.
        """
        seed_str = f"{self.seed}:{tick_id}:{state_hash}:{node_id}"
        seed_int = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
        return random.Random(seed_int)
