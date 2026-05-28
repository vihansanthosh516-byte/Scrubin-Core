import pytest
from scrubin.api.stream_manager import compute_phase

@pytest.mark.parametrize("total_ticks, phases, tick, expected_index, expected_name", [
    (50, ["entry", "visualization", "dissection", "removal", "closure"], 0, 0, "entry"),
    (50, ["entry", "visualization", "dissection", "removal", "closure"], 9, 0, "entry"),
    (50, ["entry", "visualization", "dissection", "removal", "closure"], 10, 1, "visualization"),
    (50, ["entry", "visualization", "dissection", "removal", "closure"], 49, 4, "closure"),
    # total ticks less than phases -> phase_len = 1
    (3, ["a", "b", "c", "d", "e"], 0, 0, "a"),
    (3, ["a", "b", "c", "d", "e"], 1, 1, "b"),
    (3, ["a", "b", "c", "d", "e"], 2, 2, "c"),
])
def test_compute_phase(total_ticks, phases, tick, expected_index, expected_name):
    idx, name = compute_phase(tick, total_ticks, phases)
    assert idx == expected_index
    assert name == expected_name
