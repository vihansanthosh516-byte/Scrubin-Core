"""Deterministic Outcome Forecast Engine.
+
+The engine produces an ``OutcomeForecast`` based solely on immutable snapshots of
+the current world state.  It uses deterministic rule tables – no randomness or
+ML – to compute scalar predictions (floats/ints).  The design mirrors the other
+deterministic components of Phase 7.5.
+"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Any

from .models import ComplicationState


@dataclass(frozen=True, slots=True)
class OutcomeForecast:
    """Immutable forecast of surgical outcomes.
+
+    All numeric fields are deterministic and derived from simple rule‑based
+    calculations.
+    """

    mortality_risk: float  # 0.0 – 1.0 probability (deterministic value)
    blood_loss_ml: int
    instability_score: float
    complication_progression: str
    icu_likelihood: float
    operative_difficulty: int
    expected_recovery_days: int
    expected_completion_minutes: int


@dataclass(frozen=True, slots=True)
class ForecastState:
    """Container for the most recent forecast and the input state used.
+
+    ``forecast`` holds the deterministic ``OutcomeForecast`` and ``source_hash``
+    is a simple deterministic hash of the input components for replay verification.
+    """

    forecast: OutcomeForecast
    source_hash: int

    @staticmethod
    def _deterministic_hash(
        anatomy: Mapping[str, Any],
        physiology: Mapping[str, Any],
        workflow: Mapping[str, Any],
        or_team: Mapping[str, Any],
        complications: ComplicationState,
        exec_plan: Mapping[str, Any] | None = None,
    ) -> int:
        # Combine hashes of all immutable inputs; tuples guarantee order.
        comp_ids = tuple(c.deterministic_id for c in complications.active_complications)
        return hash(
            (
                tuple(sorted(anatomy.items())),
                tuple(sorted(physiology.items())),
                tuple(sorted(workflow.items())),
                tuple(sorted(or_team.items())),
                comp_ids,
                tuple(sorted(exec_plan.items())) if exec_plan else (),
            )
        )

    @classmethod
    def from_state(
        cls,
        anatomy: Mapping[str, Any],
        physiology: Mapping[str, Any],
        workflow: Mapping[str, Any],
        or_team: Mapping[str, Any],
        complications: ComplicationState,
        exec_plan: Mapping[str, Any] | None = None,
    ) -> "ForecastState":
        forecast = OutcomeForecaster.compute(
            anatomy,
            physiology,
            workflow,
            or_team,
            complications,
            exec_plan,
        )
        src_hash = cls._deterministic_hash(anatomy, physiology, workflow, or_team, complications, exec_plan)
        return cls(forecast=forecast, source_hash=src_hash)


class OutcomeForecaster:
    """Pure deterministic compute engine for surgical outcome forecasts.
+
+    The implementation uses simple deterministic formulas based on the input
+    dictionaries.  The rules are intentionally straightforward to satisfy the
+    requirement of *no randomness* and *no external APIs*.
+    """

    @staticmethod
    def _base_risk(physiology: Mapping[str, Any]) -> float:
        # Base mortality risk derived from vitals (example deterministic mapping)
        hr = physiology.get("heart_rate", 70)
        bp = physiology.get("blood_pressure", 120)
        # Simple deterministic function – higher HR and lower BP increase risk
        risk = max(0.0, min(1.0, (hr - 60) * 0.001 + (80 - bp) * 0.002))
        return risk

    @staticmethod
    def compute(
        anatomy: Mapping[str, Any],
        physiology: Mapping[str, Any],
        workflow: Mapping[str, Any],
        or_team: Mapping[str, Any],
        complications: ComplicationState,
        exec_plan: Mapping[str, Any] | None = None,
    ) -> OutcomeForecast:
        # Mortality risk: base risk plus adjustments for complications severity
        base = OutcomeForecaster._base_risk(physiology)
        severity_sum = sum(c.severity for c in complications.active_complications)
        mortality = min(1.0, base + 0.05 * severity_sum)

        # Blood loss trajectory (ml) – base from anatomy damage plus complication influence
        damage = anatomy.get("damage", 0)
        blood_loss = int(damage * 100 + severity_sum * 200)

        # Instability score – higher HR, lower BP, and active complications increase it
        hr = physiology.get("heart_rate", 70)
        bp = physiology.get("blood_pressure", 120)
        instability = max(0.0, (hr - 70) * 0.1 + (100 - bp) * 0.05 + severity_sum * 0.2)

        # Complication progression – deterministic string based on max severity
        max_sev = max([c.severity for c in complications.active_complications] or [0])
        if max_sev >= 3:
            progression = "Critical"
        elif max_sev == 2:
            progression = "Escalating"
        elif max_sev == 1:
            progression = "Active"
        else:
            progression = "Inactive"

        # ICU likelihood – function of instability and team staffing
        staff = or_team.get("staff_available", 1)
        icu = min(1.0, instability * 0.01 + (1 - staff) * 0.2)

        # Operative difficulty – based on anatomy complexity and workflow urgency
        complexity = anatomy.get("complexity", 1)
        urgency = 1 if workflow.get("emergency", False) else 0
        difficulty = int(complexity * 2 + urgency * 3)

        # Expected recovery days – severity and ICU likelihood drive it
        recovery = int(2 + severity_sum * 1.5 + icu * 5)

        # Expected completion minutes – baseline plus adjustments for difficulty and complications
        baseline = exec_plan.get("estimated_minutes", 120) if exec_plan else 120
        completion = int(baseline + difficulty * 10 + severity_sum * 5)

        return OutcomeForecast(
            mortality_risk=mortality,
            blood_loss_ml=blood_loss,
            instability_score=instability,
            complication_progression=progression,
            icu_likelihood=icu,
            operative_difficulty=difficulty,
            expected_recovery_days=recovery,
            expected_completion_minutes=completion,
        )
