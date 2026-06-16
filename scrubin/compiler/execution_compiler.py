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

def _stage_pkpd_v2(orch) -> None:
    """Generate deterministic PK/PD v2 events (advanced two‑compartment model)."""
    from scrubin.physiology.pkpd_engine_v2 import PKPDv2Engine
    pkpd_engine = PKPDv2Engine()
    pkpd_events = pkpd_engine.generate_events(orch.world)
    orch._last_events.extend(pkpd_events)
    for ev in pkpd_events:
        orch.sim_event_queue.add(ev)

def _stage_hemodynamics(orch) -> None:
    """Generate deterministic hemodynamics events (preload, afterload, CO, baroreflex)."""
    from scrubin.physiology.hemodynamics_engine import HemodynamicsEngine
    hemo_engine = HemodynamicsEngine()
    hemo_events = hemo_engine.generate_events(orch.world)
    orch._last_events.extend(hemo_events)
    for ev in hemo_events:
        orch.sim_event_queue.add(ev)

def _stage_multi_disease_interaction(orch) -> None:
    """Generate deterministic multi‑disease interaction events."""
    from scrubin.physiology.multi_disease_interaction import MultiDiseaseInteractionEngine
    engine = MultiDiseaseInteractionEngine()
    md_events = engine.generate_events(orch.world)
    orch._last_events.extend(md_events)
    for ev in md_events:
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

# ---------------------------------------------------------------------------
# Hospital and agent stages – placeholders for deterministic logic (5.3.4‑5.3.5)
# ---------------------------------------------------------------------------

def _stage_hospital_resources(orch) -> None:
    """Compute deterministic resource snapshot for the current tick.
    """
    from scrubin.hospital.resource_registry import compute_resource_snapshot
    # Use previous snapshot if available for delta calculation
    prev = getattr(orch, "resource_snapshot", None)
    snapshot, deltas = compute_resource_snapshot(orch.world, previous_snapshot=prev)
    orch.resource_snapshot = snapshot
    orch.resource_deltas = deltas
    # No events generated at this stage


def _stage_ed_dynamics(orch) -> None:
    """Compute deterministic ED dynamics based on the resource snapshot.
    """
    from scrubin.hospital.ed_dynamics import compute_ed_dynamics
    # Ensure resource_snapshot exists – if not, compute a minimal one
    if not hasattr(orch, "resource_snapshot"):
        from scrubin.hospital.resource_registry import compute_resource_snapshot
        orch.resource_snapshot, _ = compute_resource_snapshot(orch.world)
    orch.ed_state = compute_ed_dynamics(orch.resource_snapshot)
    # No events generated


def _stage_icu_allocation(orch) -> None:
    """Deterministic ICU allocation – placeholder that denies all transfers.
    """
    from scrubin.hospital.icu_allocation import allocate_icu_beds
    # Placeholder transfer queue – empty for now
    approvals, denials = allocate_icu_beds(orch.resource_snapshot, [])
    orch.icu_approvals = approvals
    orch.icu_denials = denials
    # No events generated


def _stage_triage_queue(orch) -> None:
    """Deterministic triage processing – placeholder with no incoming patients.
    """
    from scrubin.hospital.triage_queue import process_triage
    # Placeholder empty incoming list; staff_snapshot not used in stub
    orch.triage_assignments = process_triage([], orch.resource_snapshot, None)
    # No events generated


def _stage_agent_evaluation(orch) -> None:
    """Run deterministic agents and collect their SurgicalEvent actions.
    """
    # Ensure the agent registry exists – orchestrator creates it in __init__
    if not hasattr(orch, "agent_registry"):
        from scrubin.agents.agent_registry import AgentRegistry
        orch.agent_registry = AgentRegistry()
    # Evaluate agents – pass world, physiology snapshot, and resource snapshot
    physiology_snapshot = orch.world.physiology  # mutable snapshot for agents
    events = orch.agent_registry.evaluate(orch.world, physiology_snapshot, orch.resource_snapshot)
    # Add to per‑tick event list and queue
    if events:
        orch._last_events.extend(events)
        for ev in events:
            orch.sim_event_queue.add(ev)


def _stage_agent_actions(orch) -> None:
    """Placeholder for any additional agent‑generated actions.
    Currently merged into ``_stage_agent_evaluation`` – no extra work.
    """
    pass


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
        ExecutionStage(name="pkpd_v2", handler=_stage_pkpd_v2, order=4),
        ExecutionStage(name="hemodynamics", handler=_stage_hemodynamics, order=5),
        ExecutionStage(name="multi_disease", handler=_stage_multi_disease_interaction, order=6),
        ExecutionStage(name="hidden", handler=_stage_hidden, order=7),
        ExecutionStage(name="complication", handler=_stage_complication, order=8),
        ExecutionStage(name="flush", handler=_stage_flush, order=9),
    ]
    # Deterministic ordering – sorted by ``order``.
    stages.sort(key=lambda s: s.order)
    return ExecutionPlan(stages=stages)
