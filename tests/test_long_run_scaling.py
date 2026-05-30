"""Long‑run scaling benchmark test.

Runs a 10 000‑tick simulation and checks that key state containers remain
bounded and do not exhibit uncontrolled growth.
"""

from scrubin.world.state import WorldState
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.engine.random import SimulationRNG


def test_long_run_memory_and_timeline_growth():
    rng = SimulationRNG(seed=0)
    engine = PhysiologicEvolutionEngine(rng)
    world = WorldState(tick=0, seed=0)
    max_ticks = 10000
    for _ in range(max_ticks):
        world = engine.evolve(world)

    # Timeline should not explode beyond a reasonable bound.
    # Empirically, a few hundred events per tick is excessive; we assert a
    # generous upper limit.
    assert len(world.timeline) < 500_000, "Timeline growth exceeds expected bound"

    # Tutoring interventions should remain bounded – each tick may add at most a
    # few interventions, so total active interventions should be < max_ticks.
    tutoring = world.tutoring_state
    assert len(tutoring.active_interventions) <= max_ticks

    # Ensure no duplicate intervention IDs.
    ids = [i.intervention_id for i in tutoring.active_interventions]
    assert len(ids) == len(set(ids)), "Duplicate tutoring intervention IDs detected"

    # Consequence memory growth – ensure it does not exceed max_ticks by a large
    # margin (each complication should be recorded at most once).
    # The ``consequence_memory`` attribute lives in ``scrubin.memory``; we
    # import it lazily to avoid circular imports.
    from scrubin.memory.consequence_memory import ConsequenceMemory

    # In the current world model the memory is attached via the ``WorldState``
    # through the ``consequence_memory`` attribute (populated elsewhere).  If the
    # attribute is missing we treat the size as zero.
    mem = getattr(world, "consequence_memory", ConsequenceMemory())
    # ``overload_periods`` is a tuple of timestamps; its length should be <= max_ticks.
    assert len(mem.overload_periods) <= max_ticks
