"""Tests for deterministic multi‑agent simulation (Phase 8.3)."""

from scrubin.systems.models import SystemsState, CardiovascularSystem, RespiratorySystem, RenalSystem, HepaticSystem, NeurologicSystem, EndocrineSystem, ImmuneSystem, MetabolicSystem
from scrubin.simulation.models import SimulationWorld, SimulationAgent, SimulationSnapshot
from scrubin.simulation.world_runtime import WorldRuntime


def init_world():
    env_state = None  # default EnvironmentState will be used inside SimulationWorld
    phys = SystemsState(
        cardiovascular=CardiovascularSystem(),
        respiratory=RespiratorySystem(),
        renal=RenalSystem(),
        hepatic=HepaticSystem(),
        neurologic=NeurologicSystem(),
        endocrine=EndocrineSystem(),
        immune=ImmuneSystem(),
        metabolic=MetabolicSystem(),
    )
    # SimulationWorld uses default EnvironmentState via its default field.
    from scrubin.simulation.models import EnvironmentState
    return SimulationWorld(environment=EnvironmentState(), physiology=phys, tick=0)


def test_multi_agent_determinism():
    world = init_world()
    snaps1 = WorldRuntime.run(world, ticks=3)
    snaps2 = WorldRuntime.run(world, ticks=3)
    hashes1 = [snap.deterministic_hash for snap in snaps1]
    hashes2 = [snap.deterministic_hash for snap in snaps2]
    assert hashes1 == hashes2


def test_conflict_resolution_deterministic():
    world = init_world()
    # Run one tick – agents will request instruments in deterministic order.
    snap = WorldRuntime.run(world, ticks=1)[0]
    # The first two agents should have successfully requested instruments,
    # the third and later should receive "idle" actions because only three
    # instruments are defined.
    actions = snap.actions
    requested = [a for a in actions if a.action_type == "request_instrument"]
    idle = [a for a in actions if a.action_type == "idle"]
    assert len(requested) == 3
    assert len(idle) == 2


def test_event_determinism():
    world = init_world()
    snap = WorldRuntime.run(world, ticks=1)[0]
    # Events should correspond one‑to‑one with actions and be sorted.
    event_types = [e.event_type for e in snap.events]
    # Expected order: three instrument_requested then two idle (sorted by type then details)
    # Sorted order: "idle" events come before "instrument_requested" events.
    assert event_types == ["idle", "idle", "instrument_requested", "instrument_requested", "instrument_requested"]


def test_full_tick_replay_hash_chain():
    world = init_world()
    snapshots = WorldRuntime.run(world, ticks=5)
    hash_chain = tuple(snap.deterministic_hash for snap in snapshots)
    # Replay should succeed and produce identical hashes.
    assert WorldRuntime.replay(world, hash_chain)
