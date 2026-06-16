"""Deterministic perfusion calculations for organ systems.
+
+Given global hemodynamic inputs the engine returns perfusion values for key
+organs.  The formulas are simple deterministic linear relationships.
+"""

from __future__ import annotations

from typing import Mapping, Tuple


class PerfusionEngine:
    """Stateless deterministic perfusion calculator.
+
+    Inputs:
+        * map_: mean arterial pressure (mmHg)
+        * cardiac_output: L/min
+        * vascular_resistance: arbitrary units
+        * blood_loss: ml (reduces effective MAP)
+        * vasopressor: boolean flag (adds fixed MAP boost)
+
+    Returns a mapping of organ → perfusion (ml/min) values.
+    """

    @staticmethod
    def compute(
        map_: float,
        cardiac_output: float,
        vascular_resistance: float,
        blood_loss: float,
        vasopressor: bool = False,
    ) -> Mapping[str, float]:
        # Adjust MAP for blood loss deterministically
        adjusted_map = map_ - blood_loss * 0.05
        if vasopressor:
            adjusted_map += 10.0

        # Base organ share fractions (deterministic)
        shares = {
            "brain": 0.15,
            "liver": 0.25,
            "kidney": 0.20,
            "bowel": 0.10,
            "lung": 0.30,
        }
        # Perfusion ~ MAP * CO / (VR) * share
        base = adjusted_map * cardiac_output / (vascular_resistance + 1e-3)
        return {organ: base * frac for organ, frac in shares.items()}
