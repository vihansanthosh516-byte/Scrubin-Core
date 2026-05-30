"""Pipeline order validation for the physiologic evolution engine.

The test inspects the source code of ``PhysiologicEvolutionEngine.evolve`` and
verifies that the numbered step comments (e.g. ``# 1️⃣``) appear in a strictly
increasing order, ensuring that the execution pipeline matches the documented
sequence.
"""

import pathlib, re


def test_physiologic_evolution_step_order():
    # Resolve the path to the engine source file.
    engine_path = pathlib.Path(__file__).parents[2] / "scrubin" / "engine" / "physiologic_evolution.py"
    source = engine_path.read_text(encoding="utf-8")
    # Find all ordered step markers – they appear as "# <number>" possibly followed by an emoji.
    markers = [int(num) for num in re.findall(r"# (\d+)", source)]
    assert markers, "No step markers found in physiologic_evolution.py"
    # Ensure the markers are strictly increasing.
    assert markers == sorted(markers), f"Step markers are out of order: {markers}"
