"""Compile a deterministic execution plan for ScrubIn Core.

The compiler inspects no runtime state – it merely assembles a fixed list of
stage handlers that will be invoked each tick.  The handlers are defined
below and operate on the live ``Orchestrator`` instance, mutating its world,
event queue and temporary bookkeeping attributes.
"""

from __future__ import annotations

from typing import List

from .execution_plan import ExecutionStage, ExecutionPlan

# ---------------------------------------------------------------------------
# Stage handler implementations – each receives the orchestrator instance.
# ---------------------------------------------------------------------------

def _stage_physiology(orch) -> None:
    """Generate physiology events and store timeline information.

    The immutable ``WorldState`` snapshot is built from the current mutable
    ``SimulationWorld`` to satisfy the deterministic physiology engine.
    """
    from scrubin.world.state import WorldState, PhysiologicalState, CardiovascularState, RespiratoryState, ComplicationWorldState
    from scrubin.engine.physiology_events import generate_physiology_events
    from scrubin.engine.random import SimulationRNG

    vitals = orch.world.physiology.vitals
    cardio = CardiovascularState(
        map=vitals.get("map", 100.0),
        heart_rate=vitals.get("heart_rate", 80.0),
    )
    resp = RespiratoryState(
        spo2=vitals.get("spo2", 98.0),
    )
    phys_state = PhysiologicalState(vitals=vitals, cardiovascular=cardio, respiratory=resp)
    immutable_world = WorldState(
        tick=orch.world.tick,
        physiology=phys_state,
        complications=ComplicationWorldState(),
        hidden_effects=tuple(),
    )
    phy_events, phy_timeline = generate_physiology_events(immutable_world, SimulationRNG(orch.seed))

    # initialise per‑tick bookkeeping structures
    orch._last_events = list(phy_events)
    orch._phy_timeline = phy_timeline

    for ev in phy_events:
        orch.sim_event_queue.add(ev)


def _stage_disease(orch) -> None:
    """Generate deterministic disease‑progression events.
    """
    from scrubin.physiology.disease_progression import DiseaseProgressionEngine
    disease_engine = DiseaseProgressionEngine()
    disease_events = disease_engine.generate_events(orch.world)
    orch._last_events.extend(disease_events)
    for ev in disease_events:
        orch.sim_event_queue.add(ev)


def _stage_pkpd(orch) -> None:
    """Generate deterministic PK/PD events.
    """
    from scrubin.physiology.pkpd_engine import PKPDEngine
    pkpd_engine = PKPDEngine()
    pkpd_events = pkpd_engine.generate_events(orch.world)
    orch._last_events.extend(pkpd_events)
    for ev in pkpd_events:
        orch.sim_event_queue.add(ev)


def _stage_hidden(orch) -> None:
    """Generate hidden‑state propagation events.
    """
    from scrubin.engine.hidden_state_propagation import apply_hidden_state_propagation
    hidden_events = apply_hidden_state_propagation(orch.world)
    orch._last_events.extend(hidden_events)
    for ev in hidden_events:
        orch.sim_event_queue.add(ev)


def _stage_complication(orch) -> None:
    """Generate complication events.
    """
    from scrubin.engine.complication_events import generate_complication_events
    comp_events = generate_complication_events(orch.world)
    orch._last_events.extend(comp_events)
    for ev in comp_events:
        orch.sim_event_queue.add(ev)


def _stage_flush(orch) -> None:
    """Process the accumulated event queue in a single deterministic pass.
    """
    from scrubin.events.event_processor import process_events
    orch.world, orch.sim_event_queue = process_events(
        orch.world, orch.sim_event_queue, authority=orch.authority
    )
    # Apply any physiology timeline events that were generated earlier.
    phy_tl = getattr(orch, "_phy_timeline", None)
    if phy_tl:
        orch.world.append_timeline(phy_tl)


def compile_execution_plan(orchestrator) -> ExecutionPlan:
    """Create a deterministic ``ExecutionPlan`` for the given orchestrator.

    The plan is static – it only depends on the orchestrator's configuration
    (e.g., the presence of a PK/PD subsystem).  For now we always include the
    full set of stages because the benchmark suite exercises every subsystem.
    """
    stages: List[ExecutionStage] = [
        ExecutionStage(name="physiology", handler=_stage_physiology, order=1),
        ExecutionStage(name="disease", handler=_stage_disease, order=2),
        ExecutionStage(name="pkpd", handler=_stage_pkpd, order=3),
        ExecutionStage(name="hidden", handler=_stage_hidden, order=4),
        ExecutionStage(name="complication", handler=_stage_complication, order=5),
        ExecutionStage(name="flush", handler=_stage_flush, order=6),
    ]
    # Deterministic ordering – sorted by ``order``.
    stages.sort(key=lambda s: s.order)
    return ExecutionPlan(stages=stages)
