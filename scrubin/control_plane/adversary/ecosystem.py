"""Adversary Ecosystem (P6.4)

This module implements a deterministic multi‑adversary environment. Multiple
adversaries (currently based on the adaptive adversary from P6.3) are registered
under string identifiers. On each tick the ecosystem gathers each adversary's
fault injection decisions, merges them deterministically, and returns a flat
list of :class:`ByzantineEvent` objects.

The design preserves replayability:

* All randomness is derived from the tick, world ``state_hash`` and an optional
  seed.
* The merge order is deterministic (by sorting on a stable key).
* Each adversary maintains its own persistent ``AdversaryMemory``.
"""

import json
import hashlib
from typing import Dict, List, Any

from .adaptive import AdaptiveAdversary
from .byzantine import ByzantineEvent


class AdversaryEcosystem:
    """P6.4: Multi‑adversary deterministic ecosystem.

    The ecosystem holds a registry of named adversaries (instances of
    :class:`AdaptiveAdversary` or any compatible object providing an ``inject``
    method with the same signature).  On ``inject_all`` each adversary receives
    the same snapshot of events, tick, and state hash, optionally together with a
    per‑adversary ``feedback`` signal.  The resulting :class:`ByzantineEvent`
    objects are merged into a deterministic order.
    """

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.adversaries: Dict[str, AdaptiveAdversary] = {}

    # -----------------------------------------------------------------
    def register(self, name: str, adversary: AdaptiveAdversary) -> None:
        """Add an adversary under ``name``.

        If ``name`` already exists it will be overwritten.
        """
        self.adversaries[name] = adversary

    # -----------------------------------------------------------------
    def inject_all(
        self,
        events: List[Dict[str, Any]],
        tick_id: int,
        state_hash: str,
        node_id: str = "node-0",
        feedback_map: Dict[str, float] | None = None,
    ) -> List[ByzantineEvent]:
        """Collect fault injections from all registered adversaries.

        Parameters
        ----------
        events:
            List of raw event dictionaries.
        tick_id:
            Current simulation tick.
        state_hash:
            SHA‑256 hash of the world state for this tick.
        node_id:
            Identifier of the node being corrupted.
        feedback_map:
            Optional mapping ``name -> feedback`` to feed each adversary. Missing
            entries default to ``0.0``.
        """
        feedback_map = feedback_map or {}
        all_events: List[ByzantineEvent] = []

        for name, adv in self.adversaries.items():
            feedback = feedback_map.get(name, 0.0)
            # Each adversary returns a list of ByzantineEvent objects.
            adv_out = adv.inject(
                events,
                tick_id=tick_id,
                state_hash=state_hash,
                node_id=node_id,
                feedback=feedback,
            )
            all_events.extend(adv_out)

        # Deterministic merging – sort by a stable key derived from the event.
        return self._merge(all_events)

    # -----------------------------------------------------------------
    @staticmethod
    def _merge(events: List[ByzantineEvent]) -> List[ByzantineEvent]:
        """Deterministically order a list of ``ByzantineEvent`` objects.

        The ordering is based on a SHA‑256 digest of the tuple that uniquely
        identifies an event: ``(tick_id, node_id, fault_type, original)``.
        ``original`` is serialized to JSON with sorted keys to guarantee stable
        representation.
        """
        def sort_key(ev: ByzantineEvent) -> str:
            # Serialize the original event deterministically.
            orig_json = json.dumps(ev.original, sort_keys=True)
            composite = f"{ev.tick_id}:{ev.node_id}:{ev.fault_type}:{orig_json}"
            return hashlib.sha256(composite.encode()).hexdigest()

        # ``sorted`` is stable, so events with identical keys keep insertion order.
        return sorted(events, key=sort_key)
