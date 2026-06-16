"""Deterministic feedback engine for organ systems.
+
+Implements explicit positive and negative feedback loops using pure functions.
+All loops are bounded and terminate after a single deterministic update per
+tick.
+"""

from __future__ import annotations

from typing import Tuple

from .models import (
    CardiovascularSystem,
    RespiratorySystem,
    RenalSystem,
    HepaticSystem,
    NeurologicSystem,
    EndocrineSystem,
    ImmuneSystem,
    MetabolicSystem,
)


class FeedbackEngine:
    """Deterministic feedback loop processing.
+
+    Two example loops are encoded:
+    * Hemorrhage → hypotension → reduced perfusion → further hypotension
+      (positive feedback) – capped by a deterministic factor.
+    * Hypoxia → increased respiratory drive → improved oxygen delivery →
+      reduced stress (negative feedback).
+    The method returns updated system objects; loops are applied once per tick.
+    """

    @staticmethod
    def process(
        cardio: CardiovascularSystem,
        resp: RespiratorySystem,
        renal: RenalSystem,
        hep: HepaticSystem,
        neuro: NeurologicSystem,
        endocrine: EndocrineSystem,
        immune: ImmuneSystem,
        metabolic: MetabolicSystem,
    ) -> Tuple[
        CardiovascularSystem,
        RespiratorySystem,
        RenalSystem,
        HepaticSystem,
        NeurologicSystem,
        EndocrineSystem,
        ImmuneSystem,
        MetabolicSystem,
    ]:
        # Positive feedback: blood loss (simulated via cardio stress) amplifies hypotension
        hypotension_factor = min(1.0, cardio.stress_level * 0.02)
        new_perf = max(0.0, cardio.perfusion * (1 - hypotension_factor))
        cardio2 = cardio.update(perfusion=new_perf, stress_level=cardio.stress_level + hypotension_factor * 5)

        # Negative feedback: hypoxia (respiratory stress) triggers increased drive
        hypoxia = resp.stress_level
        drive_increase = min(5.0, hypoxia * 0.5)
        resp2 = resp.update(compensation_level=resp.compensation_level + int(drive_increase))
        # Assume improved oxygen delivery reduces overall systemic stress slightly
        systemic_reduction = drive_increase * 0.1
        cardio2 = cardio2.update(stress_level=max(0.0, cardio2.stress_level - systemic_reduction))
        renal2 = renal.update(stress_level=max(0.0, renal.stress_level - systemic_reduction))
        hep2 = hep.update(stress_level=max(0.0, hep.stress_level - systemic_reduction))
        neuro2 = neuro.update(stress_level=max(0.0, neuro.stress_level - systemic_reduction))
        endocrine2 = endocrine.update(stress_level=max(0.0, endocrine.stress_level - systemic_reduction))
        immune2 = immune.update(stress_level=max(0.0, immune.stress_level - systemic_reduction))
        metabolic2 = metabolic.update(stress_level=max(0.0, metabolic.stress_level - systemic_reduction))

        return (
            cardio2,
            resp2,
            renal2,
            hep2,
            neuro2,
            endocrine2,
            immune2,
            metabolic2,
        )
