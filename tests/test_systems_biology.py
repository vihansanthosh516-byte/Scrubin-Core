"""Tests for Systems Biology Engine integration.

The tests verify deterministic evolution of the new biological subsystems
and ensure replay safety.
"""

from __future__ import annotations

from dataclasses import replace

from scrubin.world.state import WorldState, AnatomicalState
from scrubin.anatomy.state import AnatomicalRegion, Injury
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.engine.random import SimulationRNG


def _make_world(map_value=100.0, anatomy=None):
    rng = SimulationRNG(seed=0)
    engine = PhysiologicEvolutionEngine(rng)
    world = WorldState(tick=0, seed=0)
    if map_value != 100.0:
        cardio = world.physiology.cardiovascular.with_map(map_value)
        phys = replace(world.physiology, cardiovascular=cardio)
        world = world.with_physiology(phys)
    if anatomy is not None:
        world = world.with_anatomy(anatomy)
    return engine, world


def test_inflammatory_escalation():
    injury = Injury(type='vascular', severity=0.5, occult=False, onset_tick=0, reveal_threshold=0)
    region = AnatomicalRegion(id='kidney', name='Kidney').add_injury(injury)
    anatomy = AnatomicalState(regions=(region,))
    engine, world = _make_world(anatomy=anatomy)
    world = engine.evolve(world)
    assert world.biology.inflammatory.level > 0.0
    assert any(ev.description == 'inflammatory_escalation' for ev in world.timeline)


def test_oxygen_debt_and_shock():
    engine, world = _make_world(map_value=55.0)
    world = engine.evolve(world)
    assert world.biology.oxygen_debt.debt > 0.0
    assert world.biology.shock.shock_type != 'none'
    descriptions = {ev.description for ev in world.timeline}
    assert 'oxygen_debt_increasing' in descriptions
    assert 'systemic_decompensation' in descriptions


def test_coagulation_and_necrosis():
    injury = Injury(type='thermal', severity=0.3, occult=False, onset_tick=0, reveal_threshold=0)
    region = AnatomicalRegion(id='liver', name='Liver', ischemia=True).add_injury(injury)
    anatomy = AnatomicalState(regions=(region,))
    engine, world = _make_world(anatomy=anatomy, map_value=70.0)
    world = engine.evolve(world)
    assert world.biology.coagulation.clot_level > 0.0
    assert world.biology.necrosis.level > 0.0
    descriptions = {ev.description for ev in world.timeline}
    assert 'coagulation_instability' in descriptions
    assert 'tissue_necrosis_progressing' in descriptions


def test_replay_consistency():
    injury = Injury(type='vascular', severity=0.4, occult=False, onset_tick=0, reveal_threshold=0)
    region = AnatomicalRegion(id='spleen', name='Spleen').add_injury(injury)
    anatomy = AnatomicalState(regions=(region,))
    def run():
        engine, world = _make_world(map_value=65.0, anatomy=anatomy)
        for _ in range(3):
            world = engine.evolve(world)
        return world
    w1 = run()
    w2 = run()
    assert w1 == w2
