'''Deterministic simulation preview engine.

The ``SimulationPreviewEngine`` predicts the outcome of a candidate adaptive
plan using deterministic rule evaluation – no Monte‑Carlo or random sampling is
performed. The preview derives simple numeric estimates from the plan’s
deterministic hash, ensuring that identical inputs always produce identical
outputs.
''' 

from __future__ import annotations

import hashlib
from typing import Mapping, Any

from .models import AdaptivePlan, SimulationPreview


class SimulationPreviewEngine:
    """Produce a deterministic preview of an ``AdaptivePlan``.

    The preview generates placeholder physiology and complication data by hashing
    the plan identifier. All derived values are deterministic and reproducible.
    """

    def __init__(self) -> None:
        pass

    @staticmethod
    def _hash_to_float(hash_str: str, scale: float = 1.0) -> float:
        """Convert the first 8 characters of a SHA‑256 hash to a float in ``[0, scale]``.

        The conversion is deterministic and does not depend on Python's random
        module.
        """
        # Take the first 8 hex characters → 32‑bit integer.
        int_val = int(hash_str[:8], 16)
        max_int = 0xFFFFFFFF
        return (int_val / max_int) * scale

    def preview(self, plan: AdaptivePlan) -> SimulationPreview:
        """Return a deterministic ``SimulationPreview`` for ``plan``.

        The numeric fields are simple deterministic functions of the plan's hash.
        ``predicted_physiology`` and ``complication_progression`` are minimal
        dictionaries containing a few illustrative metrics.
        """
        base_hash = plan.deterministic_hash
        # Derive deterministic scalar estimates.
        operative_delay = self._hash_to_float(base_hash, scale=30.0)  # up to 30 minutes
        blood_loss_estimate = self._hash_to_float(base_hash, scale=1500.0)  # up to 1500 ml
        stability_estimate = 1.0 - self._hash_to_float(base_hash, scale=1.0)  # 0–1
        confidence = 0.95  # static high confidence for deterministic preview

        # Simple example physiology values.
        predicted_physiology: Mapping[str, Any] = {
            "heart_rate": 70 + int(self._hash_to_float(base_hash, scale=30)),
            "blood_pressure_systolic": 110 + int(self._hash_to_float(base_hash, scale=20)),
            "blood_pressure_diastolic": 70 + int(self._hash_to_float(base_hash, scale=15)),
        }
        complication_progression: Mapping[str, Any] = {
            "hemorrhage": self._hash_to_float(base_hash, scale=1.0),
            "hypoxia": self._hash_to_float(base_hash, scale=1.0),
        }
        return SimulationPreview(
            predicted_physiology=predicted_physiology,
            complication_progression=complication_progression,
            operative_delay=operative_delay,
            blood_loss_estimate=blood_loss_estimate,
            stability_estimate=stability_estimate,
            confidence=confidence,
            plan_id=plan.plan_id,
        )
