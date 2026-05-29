"""Simplified complication engine.

The existing system already has a :class:`scrubin.agents.complication.ComplicationAgent`
which drives complication lifecycles.  This lightweight ``ComplicationEngine``
provides a programmatic API that can be used by higher‑level procedural logic –
for example to schedule a deterministic complication after a specific decision
or to query the current active complication set.

It deliberately does **not** replace the agent; it merely mirrors the core
behaviour in a test‑friendly, synchronous fashion.
"""

from __future__ import annotations

# Deterministic RNG – the engine now receives an explicit ``SimulationRNG``
# instance for any stochastic decisions.  The module no longer uses the
# global ``random`` module to preserve replay invariance.

from typing import Dict, List

from scrubin.models.types import ComplicationState, ComplicationSeverity
from .random import SimulationRNG
from scrubin.complications.registry import ComplicationRegistry


class ComplicationEngine:
    """Manage active complications and their progression.

    The engine holds a mapping of complication identifiers to :class:`ComplicationState`
    objects.  It can add new complications, evaluate escalation rules, and apply
    physiologic deltas to a ``world`` object that follows the ``SimulationWorld``
    interface (i.e. has a ``physiology.vitals`` dictionary).
    """

    def __init__(self) -> None:
        self._active: Dict[str, ComplicationState] = {}

    # ---------------------------------------------------------------------
    # Public API – mutation
    # ---------------------------------------------------------------------
    def add_complication(self, comp_id: str, severity: ComplicationSeverity, tick: int) -> ComplicationState:
        """Create and store a new complication.

        Parameters
        ----------
        comp_id:
            Identifier from the registry (e.g. ``"hemorrhage"``).
        severity:
            Initial severity – ``"mild"``, ``"moderate"`` or ``"severe"``.
        tick:
            Simulation tick at which the complication appears.
        """
        state = ComplicationState(id=comp_id, severity=severity, onset_tick=tick)
        self._active[comp_id] = state
        return state

    def get_active(self) -> List[ComplicationState]:
        """Return a list of currently tracked complications."""
        return list(self._active.values())

    # ---------------------------------------------------------------------
    # Progression logic
    # ---------------------------------------------------------------------
    def maybe_escalate(self, tick: int, rng: "SimulationRNG") -> List[ComplicationState]:
        """Apply escalation rules probabilistically using a deterministic RNG.

        ``rng`` provides a dedicated ``complications`` stream.  The method returns a
        list of complications whose severity changed during this tick.
        """
        escalated: List[ComplicationState] = []
        for comp in list(self._active.values()):
            esc_rule = ComplicationRegistry.escalation_for(comp.id)
            if not esc_rule or not esc_rule.next:
                continue
            # Use the deterministic complications stream.
            if rng.complications.random() < esc_rule.probability:
                new_state = ComplicationState(
                    id=comp.id,
                    severity=esc_rule.next,  # type: ignore[arg-type]
                    onset_tick=comp.onset_tick,
                )
                self._active[comp.id] = new_state
                escalated.append(new_state)
        return escalated

    # ---------------------------------------------------------------------
    # Physiology integration
    # ---------------------------------------------------------------------
    def apply_to_world(self, world) -> None:
        """Apply the current complications' physiological impact to ``world``.

        ``world`` is expected to expose ``world.physiology.vitals`` – a mutable
        ``dict`` mapping vital names to float values.
        """
        vitals = world.physiology.vitals
        for comp in self._active.values():
            delta = ComplicationRegistry.severity_profile(comp.id, comp.severity)
            if delta is None:
                continue
            for key, val in delta.to_dict().items():
                vitals[key] = vitals.get(key, 0.0) + val
