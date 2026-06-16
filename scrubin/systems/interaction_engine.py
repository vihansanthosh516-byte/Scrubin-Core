"""Deterministic inter‑system interaction engine.

The engine takes a ``SystemsState`` snapshot and propagates the effect of one
system onto another using purely deterministic arithmetic.  No randomness,
no external services – just functional updates via ``replace``.
"""

from __future__ import annotations

from dataclasses import replace

from .models import SystemsState, CardiovascularSystem


class InteractionEngine:
    @staticmethod
    def propagate(state: SystemsState) -> SystemsState:
        """Iteratively propagate deterministic interactions across all systems.

        The propagation runs a fixed‑point loop (max 4 iterations) applying the
        deterministic coupling logic, feedback, homeostasis, perfusion and
        metabolism in each iteration.  The loop stops early when the state hash
        stops changing, guaranteeing convergence and determinism.
        """
        max_iters = 4
        prev_hash = None
        for _ in range(max_iters):
            # Core deterministic couplings
            state = InteractionEngine.evaluate(state)
            # Feedback loops (positive/negative)
            from .feedback_engine import FeedbackEngine
            state = FeedbackEngine.evaluate(state)
            # Homeostatic compensation
            from .homeostasis_engine import HomeostasisEngine
            state = HomeostasisEngine.evaluate(state)
            # Perfusion updates based on cardiovascular parameters
            from .perfusion_engine import PerfusionEngine
            state = PerfusionEngine.evaluate(state)
            # Metabolism updates
            from .metabolism_engine import MetabolismEngine
            state = MetabolismEngine.evaluate(state)
            # Check convergence
            cur_hash = state.deterministic_hash
            if cur_hash == prev_hash:
                break
            prev_hash = cur_hash
        return state

    @staticmethod
    def evaluate(state: SystemsState) -> SystemsState:
        """Core deterministic interaction logic (used internally)."""
        cv: CardiovascularSystem = state.cardiovascular

        # ---- Cardiovascular → Renal ------------------------------------------------
        new_renal_perf = state.renal.perfusion * cv.perfusion
        renal = replace(state.renal, perfusion=new_renal_perf)

        # ---- Renal → Cardiovascular (bidirectional) --------------------------------
        # Simple rule: reduced renal perfusion slightly raises cardiovascular stress.
        renal_deficit = max(0.0, 0.5 - new_renal_perf)
        cv = replace(cv, stress_level=cv.stress_level + renal_deficit * 0.5)

        # ---- Renal → Metabolic (stress increase) ----------------------------------
        stress_inc = renal_deficit * 2.0  # proportional increase
        metabolic = replace(state.metabolic, stress_level=state.metabolic.stress_level + stress_inc)

        # ---- Metabolic → Cardiovascular stress ------------------------------------
        cv = replace(cv, stress_level=cv.stress_level + stress_inc)

        # ---- Cardiovascular → Respiratory oxygen delivery ---------------------------
        resp = replace(
            state.respiratory,
            oxygen_delivery=state.respiratory.oxygen_delivery * cv.oxygen_delivery,
        )

        # ---- Respiratory → Neurologic cognitive stress (hypoxia) -------------------
        if state.respiratory.oxygen_delivery < 0.8:
            neuro = replace(state.neurologic, stress_level=state.neurologic.stress_level + 0.3)
        else:
            neuro = state.neurologic

        # ---- Neurologic → Respiratory (bidirectional) ------------------------------
        # Simple rule: higher neurologic stress reduces respiratory oxygen delivery.
        if neuro.stress_level > 1.0:
            resp = replace(resp, oxygen_delivery=resp.oxygen_delivery * 0.9)

        # ---- Cardiovascular → Hepatic perfusion ------------------------------------
        hepatic = replace(state.hepatic, perfusion=state.hepatic.perfusion * cv.perfusion)

        # ---- Hepatic dysfunction → coagulopathy (modeled as hepatic stress) --------
        if state.hepatic.perfusion < 0.7:
            hepatic = replace(hepatic, stress_level=hepatic.stress_level + 0.4)

        # ---- Immune ↔ Metabolic bidirectional --------------------------------------
        immune = replace(state.immune, stress_level=state.immune.stress_level + stress_inc)
        if state.immune.stress_level > 1.0:
            metabolic = replace(metabolic, stress_level=metabolic.stress_level + 0.5)

        # ---- Cardiovascular → Neurologic stress -----------------------------------
        neuro = replace(neuro, stress_level=neuro.stress_level + cv.stress_level * 0.5)

        # ---- Cardiovascular → Endocrine compensation ------------------------------
        endocrine = replace(state.endocrine, compensation_level=state.endocrine.compensation_level + cv.stress_level * 0.2)

        # ---- Low MAP → renal perfusion decline and fluid retention signal -----------
        if cv.map < 90.0:
            renal = replace(renal, perfusion=renal.perfusion * 0.9, stress_level=renal.stress_level + 0.2)

        # ---- Metabolic demand → cardiovascular compensation (tachycardia) ----------
        if metabolic.stress_level > 1.0:
            cv = replace(cv, stress_level=cv.stress_level + 0.3)

        # Return a brand‑new immutable snapshot.
        return replace(
            state,
            cardiovascular=cv,
            respiratory=resp,
            renal=renal,
            hepatic=hepatic,
            neurologic=neuro,
            endocrine=endocrine,
            immune=immune,
            metabolic=metabolic,
        )
    @staticmethod
    def propagate(state: SystemsState) -> SystemsState:
        """Run full deterministic interaction pipeline.

        The pipeline applies:
        1. Core cross‑system interactions (InteractionEngine.evaluate)
        2. Homeostatic compensation (HomeostasisEngine.evaluate)
        3. Feedback loops (FeedbackEngine.evaluate)
        4. Perfusion calculation (PerfusionEngine.evaluate)
        5. Metabolic updates (MetabolismEngine.evaluate)

        Each step receives the ``SystemsState`` returned by the previous step
        and produces a new immutable ``SystemsState`` via ``replace``.
        """
        # Step 1: basic deterministic coupling
        state = InteractionEngine.evaluate(state)
        # Step 2: homeostatic compensation
        from .homeostasis_engine import HomeostasisEngine
        state = HomeostasisEngine.evaluate(state)
        # Step 3: feedback loops
        from .feedback_engine import FeedbackEngine
        state = FeedbackEngine.evaluate(state)
        # Step 4: perfusion updates based on cardiovascular parameters
        from .perfusion_engine import PerfusionEngine
        state = PerfusionEngine.evaluate(state)
        # Step 5: metabolism updates
        from .metabolism_engine import MetabolismEngine
        state = MetabolismEngine.evaluate(state)
        return state
    """Engine that propagates deterministic cross‑system interactions.

    The ``propagate`` method applies a deterministic cascade of effects across
    organ systems as required by Phase 7.6.  It builds on the existing ``evaluate``
    helper but adds the specific couplings listed in the task description.
    """

    """Pure deterministic interaction logic between organ systems.

    The implementation is intentionally simple – it captures the canonical chain
    described in the specification (cardiovascular → renal → metabolic → …) but
    remains fully deterministic and side‑effect free.
    """

    @staticmethod
    def evaluate(state: SystemsState) -> SystemsState:
        """Core deterministic interaction logic (used internally)."""
        """Return a new ``SystemsState`` after applying deterministic interactions.

        The rules are illustrative yet deterministic:

        * Cardiovascular perfusion scales renal perfusion.
        * Reduced renal perfusion raises metabolic stress (simulating acidosis).
        * Metabolic stress feeds back into cardiovascular stress.
        * Cardiovascular oxygen delivery influences respiratory oxygen delivery.
        * Hepatic perfusion follows cardiovascular perfusion.
        * Immune stress rises with metabolic stress.
        * Neurologic stress rises with cardiovascular stress.
        * Endocrine compensation rises with cardiovascular stress.
        """
        cv: CardiovascularSystem = state.cardiovascular

        # ---- Cardiovascular → Renal ------------------------------------------------
        new_renal_perf = state.renal.perfusion * cv.perfusion
        renal = replace(state.renal, perfusion=new_renal_perf)

        # ---- Renal → Metabolic (stress increase) ----------------------------------
        # Simple deterministic mapping: if renal perfusion below 0.5, raise stress.
        renal_deficit = max(0.0, 0.5 - new_renal_perf)
        stress_inc = renal_deficit * 2.0  # proportional increase
        metabolic = replace(state.metabolic, stress_level=state.metabolic.stress_level + stress_inc)

        # ---- Metabolic → Cardiovascular stress ------------------------------------
        cv = replace(cv, stress_level=cv.stress_level + stress_inc)

        # ---- Cardiovascular → Respiratory oxygen delivery ---------------------------
        resp = replace(
            state.respiratory,
            oxygen_delivery=state.respiratory.oxygen_delivery * cv.oxygen_delivery,
        )

        # ---- Cardiovascular → Hepatic perfusion ------------------------------------
        hepatic = replace(state.hepatic, perfusion=state.hepatic.perfusion * cv.perfusion)

        # ---- Metabolic → Immune stress --------------------------------------------
        immune = replace(state.immune, stress_level=state.immune.stress_level + stress_inc)

        # ---- Cardiovascular → Neurologic stress -----------------------------------
        neuro = replace(state.neurologic, stress_level=state.neurologic.stress_level + cv.stress_level * 0.5)

        # ---- Cardiovascular → Endocrine compensation ------------------------------
        endocrine = replace(state.endocrine, compensation_level=state.endocrine.compensation_level + cv.stress_level * 0.2)

        # ---- Additional required couplings ---------------------------------------
        # Low MAP → renal perfusion decline and fluid retention signal
        if cv.map < 90.0:
            # reduce renal perfusion further and increase renal stress (fluid retention)
            renal = replace(renal, perfusion=renal.perfusion * 0.9, stress_level=renal.stress_level + 0.2)
        # Respiratory hypoxia → neurologic cognitive stress
        if state.respiratory.oxygen_delivery < 0.8:
            neuro = replace(neuro, stress_level=neuro.stress_level + 0.3)
        # Hepatic dysfunction → coagulopathy (modelled as hepatic stress increase)
        if state.hepatic.perfusion < 0.7:
            hepatic = replace(hepatic, stress_level=hepatic.stress_level + 0.4)
        # Immune activation → increased metabolic demand
        if state.immune.stress_level > 1.0:
            metabolic = replace(metabolic, stress_level=metabolic.stress_level + 0.5)
        # Metabolic demand → cardiovascular compensation (tachycardia)
        if metabolic.stress_level > 1.0:
            cv = replace(cv, stress_level=cv.stress_level + 0.3)

        # Return a brand‑new immutable snapshot.
        return replace(
            state,
            cardiovascular=cv,
            respiratory=resp,
            renal=renal,
            hepatic=hepatic,
            neurologic=neuro,
            endocrine=endocrine,
            immune=immune,
            metabolic=metabolic,
        )
