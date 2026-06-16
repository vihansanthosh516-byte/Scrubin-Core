"""Deterministic organ interaction engine.
+
+The engine receives a tuple of system instances and returns a new tuple with
+deterministically propagated effects.  The logic is intentionally simple but
+covers the cascades described in the specification.
+"""

from __future__ import annotations

from typing import Tuple, List

from .models import (
    CardiovascularSystem,
    RespiratorySystem,
    RenalSystem,
    HepaticSystem,
    NeurologicSystem,
    ImmuneSystem,
    EndocrineSystem,
    MetabolicSystem,
)


class OrganInteractionEngine:
    """Stateless deterministic propagation of organ‑system effects.
+
+    The implementation follows a fixed rule order that mimics the cascade:
+    1. Cardiovascular stress reduces renal perfusion.
+    2. Reduced renal perfusion lowers urine output → acidosis ↑ → cardiac
+       stress ↑.
+    3. Hepatic dysfunction raises coagulopathy → bleeding risk ↑.
+    4. Immune activation raises metabolic demand.
+    5. Respiratory failure raises hypoxia → neurologic stress.
+
+    Each step uses immutable ``replace`` updates and deterministic arithmetic.
+    The method returns a new tuple of updated system objects preserving the
+    original ordering.
+    """

    @staticmethod
    def propagate(
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
        # 1. Cardiovascular stress influences renal perfusion
        renal_perf = max(0.0, renal.perfusion - cardio.stress_level * 0.1)
        renal2 = renal.update(perfusion=renal_perf, stress_level=renal.stress_level + cardio.stress_level * 0.05)

        # 2. Renal perfusion impacts acidosis and cardiac stress
        acidosis = max(0.0, (1.0 - renal2.perfusion) * 2.0)
        cardio2 = cardio.update(
            stress_level=cardio.stress_level + acidosis * 0.2,
            oxygen_delivery=cardio.oxygen_delivery - acidosis * 0.5,
        )

        # 3. Hepatic dysfunction raises bleeding risk (reflected by stress)
        hep2 = hep.update(stress_level=hep.stress_level + cardio2.stress_level * 0.1)

        # 4. Immune activation raises metabolic demand
        metabolic2 = metabolic.update(
            oxygen_consumption=metabolic.oxygen_consumption + immune.stress_level * 0.3,
            stress_level=metabolic.stress_level + immune.stress_level * 0.2,
        )

        # 5. Respiratory failure (low perfusion) raises neurologic stress
        neuro2 = neuro.update(stress_level=neuro.stress_level + resp.stress_level * 0.15)

        # Endocrine and other systems remain unchanged for now
        endocrine2 = endocrine
        immune2 = immune
        resp2 = resp

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
