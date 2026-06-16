"""Deterministic homeostasis engine.
+
+Applies compensatory adjustments based on system stress levels.  The engine is
+pure: it takes a tuple of system objects and returns a new tuple with updated
+compensation fields.  All calculations are deterministic arithmetic.
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


class HomeostasisEngine:
    """Stateless deterministic compensation logic.
+
+    Simple rules:
+    * High cardiovascular stress → increase compensation_level (vasoconstriction).
+    * High respiratory stress → increase compensation (tachypnea).
+    * High renal stress → increase compensation (renin‑angiotensin activation).
+    * Endocrine compensation mirrors overall stress.
+    * Immune stress contributes to metabolic compensation.
+    The function returns updated system instances preserving order.
+    """

    @staticmethod
    def apply(
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
        # Cardiovascular compensation
        comp_cardio = min(10, cardio.compensation_level + int(cardio.stress_level // 2))
        cardio2 = cardio.update(compensation_level=comp_cardio)

        # Respiratory compensation
        comp_resp = min(10, resp.compensation_level + int(resp.stress_level // 2))
        resp2 = resp.update(compensation_level=comp_resp)

        # Renal compensation
        comp_renal = min(10, renal.compensation_level + int(renal.stress_level // 2))
        renal2 = renal.update(compensation_level=comp_renal)

        # Endocrine mirrors average stress
        avg_stress = (
            cardio2.stress_level
            + resp2.stress_level
            + renal2.stress_level
            + hep.stress_level
            + neuro.stress_level
            + immune.stress_level
            + metabolic.stress_level
        ) / 7.0
        endocrine2 = endocrine.update(compensation_level=int(avg_stress // 2))

        # Immune and metabolic compensation simple scaling
        immune2 = immune.update(compensation_level=int(immune.stress_level // 3))
        metabolic2 = metabolic.update(compensation_level=int(metabolic.stress_level // 3))

        # Hepatic and neurologic unchanged for now
        hep2 = hep
        neuro2 = neuro

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
