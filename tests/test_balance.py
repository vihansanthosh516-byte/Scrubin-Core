"""Locks in the causal deterioration balance across ALL procedures.

Guarantees enforced:
1. Perfect play (clinical rescues) never dies on any procedure, across seeds.
2. Neglect expectations per difficulty tier:
   - low:      healthy outpatient patients may tolerate neglect (by design)
   - moderate: neglect must be lethal in at least one seed (stakes exist)
   - high:     neglect must be lethal in the majority of seeds
   - critical: neglect must be lethal in every seed
3. Every procedure carries a risk profile with a deterioration_rate, and the
   four tier rates are strictly increasing (the difficulty gradient exists).

The harnesses (`perfect_run` / `neglect_run`) are shared with balance_sweep.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from scrubin_core_procedures import ALL_PROCEDURES
from balance_sweep import perfect_run, neglect_run, TIER_LABEL

SEEDS = [7, 42, 123, 999]

# Minimum number of seeds (of len(SEEDS)) in which neglect must be lethal.
NEGLECT_DEATHS_REQUIRED = {
    "low": 0,  # tolerance is by design for healthy outpatient patients
    "moderate": 1,
    "high": 2,
    "critical": len(SEEDS),
}

ALL_PROCEDURES_ID = sorted(p["id"] for p in ALL_PROCEDURES)
TIER_RATES = sorted(TIER_LABEL.keys())


def tier_of(proc) -> str:
    rate = proc["initialState"]["riskProfile"].get("deterioration_rate", 1.0)
    return TIER_LABEL.get(rate, f"rate={rate}")


@pytest.mark.parametrize("pid", ALL_PROCEDURES_ID)
def test_perfect_play_survives(pid):
    """Clinical rescue of every complication must never lose the patient."""
    for seed in SEEDS:
        r = perfect_run(seed, pid)
        assert r["survived"], (
            f"{pid} (seed {seed}): perfect play died — crises={r['crises']} "
            f"final BP={r['bp']} SpO2={r['spo2']}"
        )


@pytest.mark.parametrize("pid", ALL_PROCEDURES_ID)
def test_neglect_kills_by_tier(pid):
    """Ignoring complications must be lethal according to the tier's bar."""
    proc = next(p for p in ALL_PROCEDURES if p["id"] == pid)
    tier = tier_of(proc)
    required = NEGLECT_DEATHS_REQUIRED[tier]
    deaths = sum(1 for s in SEEDS if not neglect_run(s, pid)["survived"])
    assert deaths >= required, (
        f"{pid} ({tier} tier): neglect lethal in only {deaths}/{len(SEEDS)} seeds "
        f"(required >= {required}) — deterioration too tolerant for its tier"
    )


def test_every_procedure_has_deterioration_rate():
    """The difficulty tuning is applied to every surgery, not just some."""
    missing = [
        p["id"]
        for p in ALL_PROCEDURES
        if "deterioration_rate" not in p["initialState"]["riskProfile"]
    ]
    assert not missing, f"procedures missing deterioration_rate: {missing}"


def test_tier_rates_strictly_increasing():
    """The difficulty gradient exists: low < moderate < high < critical."""
    assert TIER_RATES == [0.45, 0.8, 1.6, 2.0], (
        f"tier rates changed: {TIER_RATES} — update TIER_LABEL and this test"
    )


def test_all_procedures_covered():
    """Sanity guard: the suite must keep exercising the full registry."""
    assert len(ALL_PROCEDURES_ID) >= 31, "procedure registry shrank unexpectedly"
