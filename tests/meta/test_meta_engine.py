"""Tests for the deterministic meta‑orchestration layer (Phase 8.2)."""

from scrubin.systems.models import SystemsState, CardiovascularSystem, RespiratorySystem, RenalSystem, HepaticSystem, NeurologicSystem, EndocrineSystem, ImmuneSystem, MetabolicSystem
from scrubin.meta.meta_manager import MetaManager


def init_world():
    # Minimal mock world object with a ``physiology`` attribute expected by meta engines.
    class MockWorld:
        def __init__(self, phys):
            self.physiology = phys
        # Provide deterministic_hash for consistency with MetaSnapshot hash aggregation.
        @property
        def deterministic_hash(self):
            return self.physiology.deterministic_hash

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
    return MockWorld(phys)


def test_meta_tick_determinism():
    world = init_world()
    snap1 = MetaManager.tick(world)
    snap2 = MetaManager.tick(world)
    assert snap1.deterministic_hash == snap2.deterministic_hash


def test_meta_contradiction_resolution():
    # Create a world with contradictory values: low MAP and high stress.
    class MockWorld:
        def __init__(self, phys):
            self.physiology = phys
        @property
        def deterministic_hash(self):
            return self.physiology.deterministic_hash

    phys = SystemsState(
        cardiovascular=CardiovascularSystem(map=60.0, stress_level=2.5),
        respiratory=RespiratorySystem(stress_level=2.0),
        renal=RenalSystem(stress_level=2.0),
        hepatic=HepaticSystem(),
        neurologic=NeurologicSystem(stress_level=2.0),
        endocrine=EndocrineSystem(),
        immune=ImmuneSystem(stress_level=2.0),
        metabolic=MetabolicSystem(stress_level=2.0),
    )
    world = MockWorld(phys)
    snap = MetaManager.tick(world)
    # After reconciliation low MAP should be fixed to 100 and all stress levels clamped to 1.0.
    cv = snap.state.physiology.cardiovascular
    assert cv.map == 100.0
    for name in ["respiratory", "renal", "neurologic", "immune", "metabolic"]:
        sys = getattr(snap.state.physiology, name)
        assert sys.stress_level == 1.0
