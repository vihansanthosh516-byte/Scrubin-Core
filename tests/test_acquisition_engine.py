from scrubin.search.acquisition_engine import AcquisitionEngine
from scrubin.search.experiment_history import HistoryEngine
from scrubin.search.search_models import SearchHistory


def test_grid_refinement_selects_unseen_values():
    # Simulate history where some values have been observed
    history = HistoryEngine()
    entry = SearchHistory(
        experiment_id="exp",
        run_id="run",
        replay_hash="hash",
        parameters=(("blood_loss", 0.1), ("fluids", False), ("age", 20)),
        metrics={},
        timestamp="2022-01-01",
        metadata={},
    )
    history = history.add(entry)
    candidates = AcquisitionEngine.grid_refinement(seed=0, history=history)
    assert len(candidates) == 1
    params = candidates[0].parameters
    # Expect unseen values: blood_loss -> 0.3, fluids -> True, age -> 50
    assert params["blood_loss"] == 0.3
    assert params["fluids"] == True
    assert params["age"] == 50
