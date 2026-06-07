from scrubin.search.experiment_history import HistoryEngine
from scrubin.search.search_models import SearchHistory


def test_history_engine_add_and_order():
    engine = HistoryEngine()
    entry1 = SearchHistory(
        experiment_id="b_exp",
        run_id="run1",
        replay_hash="hash1",
        parameters=(("a", 1),),
        metrics={},
        timestamp="2022-01-01",
        metadata={},
    )
    entry2 = SearchHistory(
        experiment_id="a_exp",
        run_id="run2",
        replay_hash="hash2",
        parameters=(("b", 2),),
        metrics={},
        timestamp="2022-01-02",
        metadata={},
    )
    engine2 = engine.add(entry1).add(entry2)
    histories = engine2.get_all()
    assert histories[0].experiment_id == "a_exp"
    assert histories[1].experiment_id == "b_exp"
