"""Deterministic tests for OutcomeForecaster."""

import pytest

from scrubin.complications.models import Complication, ComplicationState
from scrubin.complications.outcome_forecaster import OutcomeForecaster, ForecastState


@pytest.fixture
def sample_state():
    comp = Complication(
        deterministic_id=5,
        complication_type="bleed",
        affected_structure="arm",
        severity=2,
        progression_stage="Active",
        activation_tick=0,
        last_update_tick=0,
        active=True,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )
    return ComplicationState(active_complications=(comp,))


def test_forecast_deterministic(sample_state):
    anatomy = {"damage": 1, "complexity": 2}
    physiology = {"heart_rate": 90, "blood_pressure": 75}
    workflow = {"emergency": True}
    or_team = {"staff_available": 1}
    exec_plan = {"estimated_minutes": 150}

    forecast1 = OutcomeForecaster.compute(anatomy, physiology, workflow, or_team, sample_state, exec_plan)
    forecast2 = OutcomeForecaster.compute(anatomy, physiology, workflow, or_team, sample_state, exec_plan)
    assert forecast1 == forecast2
    # Basic sanity checks on values
    assert 0.0 <= forecast1.mortality_risk <= 1.0
    assert forecast1.blood_loss_ml > 0
    assert forecast1.expected_completion_minutes >= 150

def test_forecaststate_hash_consistency(sample_state):
    anatomy = {"damage": 0, "complexity": 1}
    physiology = {"heart_rate": 70, "blood_pressure": 120}
    workflow = {}
    or_team = {"staff_available": 2}
    fs1 = ForecastState.from_state(anatomy, physiology, workflow, or_team, sample_state)
    fs2 = ForecastState.from_state(anatomy, physiology, workflow, or_team, sample_state)
    assert fs1 == fs2
    assert fs1.source_hash == fs2.source_hash
