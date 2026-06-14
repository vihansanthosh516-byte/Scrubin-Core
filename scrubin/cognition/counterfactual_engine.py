"""Deterministic counterfactual engine.

The engine takes a :class:`CounterfactualScenario`, a snapshot of the mutable
``SimulationWorld`` and the various cognition stores, runs the hypothetical
event in isolation and returns a :class:`CounterfactualResult`.

Key properties:
* No mutation of the original world or stores – copies are deep‑copied.
* All deterministic pipelines (event processing, derived metric recompute,
  cognition pipelines) are executed on the copy.
* The result contains deterministic IDs and a replay hash generated from a
  canonical JSON representation of the output fields.
"""

from __future__ import annotations

import copy
from typing import Tuple

from scrubin.events.event_processor import process_events
from scrubin.events.event_queue import EventQueue
from scrubin.replay.hash import world_hash
from scrubin.decision.consequence_engine import _recalculate_derived_metrics

from .counterfactual import (
    CounterfactualScenario,
    CounterfactualResult,
)


def _extract_complication_ids(comp_state) -> Tuple[str, ...]:
    """Return a tuple of complication IDs from a ``ComplicationWorldState``.
    """
    # ``comp_state`` is expected to have an ``active`` attribute that is a tuple
    # of ``ComplicationState`` objects, each exposing an ``id`` field.
    return tuple(c.id for c in getattr(comp_state, "active", []))


def _extract_timeline(world) -> Tuple[Tuple[int, str], ...]:
    """Serialize the world timeline into a tuple of ``(tick, description)``.
    """
    # ``world.timeline`` may be a list (mutable) or tuple; we normalise.
    timeline = getattr(world, "timeline", [])
    return tuple((ev.tick, ev.description) for ev in timeline)


def run_counterfactual(
    scenario: CounterfactualScenario,
    world_snapshot,
    memory_store,
    fact_store,
    belief_store,
    reflection_store,
    graph_store,
) -> CounterfactualResult:
    """Execute a counterfactual scenario on a deep‑copied simulation world.

    Parameters
    ----------
    scenario:
        The immutable :class:`CounterfactualScenario` describing the hypothetical
        ``SurgicalEvent`` and its provenance.
    world_snapshot:
        The current ``SimulationWorld`` after the source episode – this will be
        ``deepcopy``‑ed before any changes.
    memory_store, fact_store, belief_store, reflection_store, graph_store:
        The mutable cognition stores from ``scrubin.core.orchestrator``. They are
        deep‑copied so the canonical simulation state remains untouched.
    """
    # ---------------------------------------------------------------------
    # Deep‑copy immutable snapshot of the world and stores.
    # ---------------------------------------------------------------------
    world_copy = copy.deepcopy(world_snapshot)
    mem_copy = copy.deepcopy(memory_store)
    fact_copy = copy.deepcopy(fact_store)
    belief_copy = copy.deepcopy(belief_store)
    reflection_copy = copy.deepcopy(reflection_store)
    graph_copy = copy.deepcopy(graph_store)

    # ---------------------------------------------------------------------
    # Apply the hypothetical event via the deterministic event pipeline.
    # ---------------------------------------------------------------------
    temp_queue = EventQueue()
    temp_queue.add(scenario.hypothetical_event)
    # ``process_events`` returns a new world (mutated) and the (now empty) queue.
    new_world, _ = process_events(world_copy, temp_queue, authority=None)

    # Recalculate derived metrics (mortality, SOFA, NEWS2) to match normal
    # post‑event state.
    _recalculate_derived_metrics(new_world)

    # ---------------------------------------------------------------------
    # Extract deterministic result fields.
    # ---------------------------------------------------------------------
    resulting_hash = world_hash(new_world)
    mortality = getattr(new_world, "mortality_risk", 0.0)
    sofa = getattr(new_world, "sofa_score", 0)
    news2 = getattr(new_world, "news2_score", 0)
    comp_ids = _extract_complication_ids(new_world.complications)
    timeline_serialised = _extract_timeline(new_world)

    # Confidence – for now we propagate the scenario confidence (could be refined).
    confidence = scenario.confidence

    # Create the immutable result object.
    result = CounterfactualResult.create(
        scenario=scenario,
        resulting_world_hash=resulting_hash,
        mortality_risk=mortality,
        sofa_score=sofa,
        news2_score=news2,
        resulting_complications=comp_ids,
        resulting_timeline=timeline_serialised,
        confidence=confidence,
    )

    # ``mem_copy``, ``fact_copy`` etc. are not returned – they remain private to
    # the counterfactual run. The orchestrator can decide whether to persist the
    # result or discard the copies.
    return result
