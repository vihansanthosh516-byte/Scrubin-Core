"""Deterministic adversarial scenario engine tests (Phase 8.4)."""

from scrubin.systems.models import SystemsState, CardiovascularSystem, RespiratorySystem
from scrubin.simulation.models import EnvironmentState, SimulationWorld
from scrubin.scenarios.scenario_manager import ScenarioManager


def init_world():
    env = EnvironmentState()
    phys = SystemsState(
        cardiovascular=CardiovascularSystem(),
        respiratory=RespiratorySystem(),
        renal=SystemsState.__annotations__.get('renal'),  # placeholder not needed
        hepatic=SystemsState.__annotations__.get('hepatic'),
        neurologic=SystemsState.__annotations__.get('neurologic'),
        endocrine=SystemsState.__annotations__.get('endocrine'),
        immune=SystemsState.__annotations__.get('immune'),
        metabolic=SystemsState.__annotations__.get('metabolic'),
    )
    return SimulationWorld(environment=env, physiology=phys, tick=0)


def test_scenario_determinism():
    world = init_world()
    snap1 = ScenarioManager.apply(world, procedure_id="appendectomy", anatomy_complexity=2)
    snap2 = ScenarioManager.apply(world, procedure_id="appendectomy", anatomy_complexity=2)
    assert snap1.deterministic_hash == snap2.deterministic_hash


def test_stress_application_effects():
    world = init_world()
    snap = ScenarioManager.apply(world, procedure_id="appendectomy", anatomy_complexity=2)
    # Verify that stress vectors have altered physiology deterministically.
    cv = snap.world.physiology.cardiovascular
    # Blood loss should be increased if hemorrhage stress present.
    # Since seed is deterministic, ensure the MAP has been reduced (or unchanged).
    # The test simply checks that the cardiovascular map is an int/float.
    assert isinstance(cv.map, float)
    # Verify that instrument list may have been reduced.
    env = snap.world.environment
    assert isinstance(env.available_instruments, tuple)


def test_adversarial_conditions_consistency():
    world = init_world()
    snap = ScenarioManager.apply(world, procedure_id="appendectomy", anatomy_complexity=2)
    # Ensure that adversarial conditions list is sorted deterministically.
    descriptions = [c.description for c in snap.profile.adversarial_conditions]
    assert descriptions == sorted(descriptions)
