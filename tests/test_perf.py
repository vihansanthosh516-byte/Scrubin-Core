from scrubin.perf.profiler import TickProfiler, TickProfile
from scrubin.perf.budgets import PerformanceBudgets
from scrubin.perf.metrics import PerformanceMetrics, TickMetrics, MCTSMetrics, HospitalMetrics
from scrubin.core.ledger import EventLedger


def test_tick_profile_dataclass():
    p = TickProfile(tick=1)
    assert p.tick == 1
    assert p.tick_duration_ms == 0.0


def test_profiler_start_end_tick():
    profiler = TickProfiler()
    profiler.start_tick(1)
    profile = profiler.end_tick()
    assert profile.tick == 1
    assert profile.tick_duration_ms >= 0


def test_profiler_phases():
    profiler = TickProfiler()
    profiler.start_tick(1)
    profiler.start_phase("evolve")
    profiler.end_phase("evolve")
    profiler.start_phase("validator")
    profiler.end_phase("validator")
    profile = profiler.end_tick()
    assert profile.evolve_duration_ms >= 0
    assert profile.validator_duration_ms >= 0


def test_profiler_profiles_list():
    profiler = TickProfiler()
    profiler.start_tick(1)
    profiler.end_tick()
    profiler.start_tick(2)
    profiler.end_tick()
    assert len(profiler.profiles) == 2


def test_profiler_latest():
    profiler = TickProfiler()
    profiler.start_tick(1)
    profiler.end_tick()
    latest = profiler.latest()
    assert latest.tick == 1


def test_profiler_latest_none():
    profiler = TickProfiler()
    assert profiler.latest() is None


def test_profiler_average_tick_ms():
    profiler = TickProfiler()
    profiler.start_tick(1)
    profiler.end_tick()
    profiler.start_tick(2)
    profiler.end_tick()
    avg = profiler.average_tick_ms()
    assert avg >= 0


def test_profiler_average_last_n():
    profiler = TickProfiler()
    for i in range(5):
        profiler.start_tick(i)
        profiler.end_tick()
    avg = profiler.average_tick_ms(last_n=3)
    assert avg >= 0


def test_profiler_ledger_event():
    ledger = EventLedger()
    profiler = TickProfiler(ledger=ledger)
    profiler.start_tick(1)
    profiler.end_tick()
    events = [e for e in ledger.all() if e.type == "tick_profile"]
    assert len(events) == 1


def test_budgets_defaults():
    b = PerformanceBudgets()
    assert b.MAX_TICK_TIME_MS == 100.0
    assert b.MAX_MCTS_NODES == 50_000
    assert b.MAX_ROLLOUTS == 10_000


def test_budgets_tick_within():
    b = PerformanceBudgets()
    assert b.check_tick_budget(50.0) is None


def test_budgets_tick_exceeded():
    b = PerformanceBudgets()
    v = b.check_tick_budget(200.0)
    assert v is not None
    assert "tick_duration" in v


def test_budgets_mcts_nodes_within():
    b = PerformanceBudgets()
    assert b.check_mcts_nodes(100) is None


def test_budgets_mcts_nodes_exceeded():
    b = PerformanceBudgets()
    v = b.check_mcts_nodes(100_000)
    assert v is not None


def test_budgets_rollouts_within():
    b = PerformanceBudgets()
    assert b.check_rollouts(100) is None


def test_budgets_rollouts_exceeded():
    b = PerformanceBudgets()
    v = b.check_rollouts(20_000)
    assert v is not None


def test_budgets_mcts_wall_time():
    b = PerformanceBudgets()
    assert b.check_mcts_wall_time(500.0) is None
    v = b.check_mcts_wall_time(2000.0)
    assert v is not None


def test_budgets_check_all():
    b = PerformanceBudgets()
    violations = b.check_all(tick_duration_ms=200.0, mcts_nodes=100_000)
    assert len(violations) == 2


def test_budgets_check_all_clean():
    b = PerformanceBudgets()
    violations = b.check_all(tick_duration_ms=50.0, mcts_nodes=100)
    assert len(violations) == 0


def test_metrics_record_tick():
    m = PerformanceMetrics()
    m.record_tick(TickMetrics(tick=1, tick_duration_ms=5.0))
    assert len(m.tick_metrics) == 1


def test_metrics_record_mcts():
    m = PerformanceMetrics()
    m.record_mcts(MCTSMetrics(node_count=100, rollout_count=50))
    assert len(m.mcts_metrics) == 1


def test_metrics_record_hospital():
    m = PerformanceMetrics()
    m.record_hospital(HospitalMetrics(patients_active=5))
    assert len(m.hospital_metrics) == 1


def test_metrics_budget_violation():
    m = PerformanceMetrics()
    m.record_budget_violation("tick too slow")
    assert len(m.budget_violations) == 1


def test_metrics_summary():
    m = PerformanceMetrics()
    m.record_tick(TickMetrics(tick=1, tick_duration_ms=5.0))
    m.record_tick(TickMetrics(tick=2, tick_duration_ms=10.0))
    s = m.summary()
    assert s["total_ticks"] == 2
    assert s["avg_tick_ms"] == 7.5
    assert s["max_tick_ms"] == 10.0


def test_metrics_ledger_event():
    ledger = EventLedger()
    m = PerformanceMetrics(ledger=ledger)
    m.record_mcts(MCTSMetrics(node_count=10, rollout_count=5))
    events = [e for e in ledger.all() if e.type == "mcts_metrics"]
    assert len(events) == 1


TESTS = [
    ("perf: TickProfile dataclass", test_tick_profile_dataclass),
    ("perf: profiler start/end tick", test_profiler_start_end_tick),
    ("perf: profiler phases", test_profiler_phases),
    ("perf: profiler profiles list", test_profiler_profiles_list),
    ("perf: profiler latest", test_profiler_latest),
    ("perf: profiler latest none", test_profiler_latest_none),
    ("perf: profiler average tick ms", test_profiler_average_tick_ms),
    ("perf: profiler average last n", test_profiler_average_last_n),
    ("perf: profiler ledger event", test_profiler_ledger_event),
    ("perf: budgets defaults", test_budgets_defaults),
    ("perf: budgets tick within", test_budgets_tick_within),
    ("perf: budgets tick exceeded", test_budgets_tick_exceeded),
    ("perf: budgets mcts nodes within", test_budgets_mcts_nodes_within),
    ("perf: budgets mcts nodes exceeded", test_budgets_mcts_nodes_exceeded),
    ("perf: budgets rollouts within", test_budgets_rollouts_within),
    ("perf: budgets rollouts exceeded", test_budgets_rollouts_exceeded),
    ("perf: budgets mcts wall time", test_budgets_mcts_wall_time),
    ("perf: budgets check all", test_budgets_check_all),
    ("perf: budgets check all clean", test_budgets_check_all_clean),
    ("perf: metrics record tick", test_metrics_record_tick),
    ("perf: metrics record mcts", test_metrics_record_mcts),
    ("perf: metrics record hospital", test_metrics_record_hospital),
    ("perf: metrics budget violation", test_metrics_budget_violation),
    ("perf: metrics summary", test_metrics_summary),
    ("perf: metrics ledger event", test_metrics_ledger_event),
]
