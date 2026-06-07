"""Pipeline order validation for the physiologic evolution engine.

The test inspects the source code of ``PhysiologicEvolutionEngine.evolve`` and
verifies that the numbered step comments (e.g. ``# 1️⃣``) appear in a strictly
increasing order, ensuring that the execution pipeline matches the documented
sequence.
"""

import pathlib, re


def test_physiologic_evolution_step_order():
    # Dynamically locate the engine source file regardless of repository name or location.
    def locate_engine() -> pathlib.Path:
        current = pathlib.Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            candidate = parent / "scrubin" / "engine" / "physiologic_evolution.py"
            if candidate.is_file():
                return candidate
        raise FileNotFoundError("physiologic_evolution.py not found")

    engine_path = locate_engine()
    source = engine_path.read_text(encoding="utf-8")
    # Find all ordered step markers – they appear as "# <number>" possibly followed by an emoji.
    markers = [int(num) for num in re.findall(r"# (\d+)", source)]
    assert markers, "No step markers found in physiologic_evolution.py"
    # Ensure the markers are strictly increasing.
    assert markers == sorted(markers), f"Step markers are out of order: {markers}"
