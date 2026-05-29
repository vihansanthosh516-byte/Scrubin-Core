"""Deterministic Systems Biology Engine.

Updates the :class:`scrubin.biology.state.SystemsBiologyState` contained in a
:class:`scrubin.world.state.WorldState`.  The engine applies a small set of
deterministic rules that couple the various sub‑systems (inflammation,
perfusion, oxygen debt, coagulation, etc.) and emits timeline events when a
notable change occurs.
"""

from __future__ import annotations

from dataclasses import replace

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.biology.state import (
    SystemsBiologyState,
    InflammatoryState,
    ImmuneActivationState,
    CoagulationState,
    PerfusionDistributionState,
    OxygenDebtState,
    MetabolicReserveState,
    AcidBaseBalanceState,
    TissueHealingState,
    NecrosisProgressionState,
    OrganDysfunctionState,
    EndocrineStressResponseState,
    SystemicShockState,
)


class SystemsBiologyEngine:
    """Deterministic evolution of the biological subsystem.

    The engine does **not** mutate any objects in‑place – it returns a new
    ``WorldState`` with an updated ``biology`` field and any generated timeline
    events.
    """

    def __init__(self, rng) -> None:  # ``rng`` retained for future extensions
        self.rng = rng

    def evolve(self, world: WorldState) -> WorldState:
        # Extract current biology and anatomy
        bio: SystemsBiologyState = world.biology
        anatomy = world.anatomy

        # -----------------------------------------------------------------
        # 1. Inflammation driven by total tissue injury severity
        # -----------------------------------------------------------------
        total_injury = sum(
            inj.severity for region in anatomy.regions for inj in region.injuries
        )
        infl: InflammatoryState = bio.inflammatory
        old_infl_level = infl.level
        new_infl_level = min(1.0, infl.level + 0.02 * total_injury)
        infl = infl.with_level(new_infl_level)
        infl = infl.with_edema(new_infl_level * 0.5)

        # -----------------------------------------------------------------
        # 2. Immune activation mirrors inflammation
        # -----------------------------------------------------------------
        immune: ImmuneActivationState = bio.immune_activation
        immune = immune.with_activation(new_infl_level * 0.8)

        # -----------------------------------------------------------------
        # 3. Perfusion – simple MAP‑based rule
        # -----------------------------------------------------------------
        perf: PerfusionDistributionState = bio.perfusion
        map_val = world.physiology.cardiovascular.map
        if map_val < 80.0:
            perf = perf.with_perf(max(0.0, perf.overall_perf - 0.04))
        else:
            perf = perf.with_perf(min(1.0, perf.overall_perf + 0.02))

        # -----------------------------------------------------------------
        # 4. Oxygen debt accumulates when perfusion insufficient
        # -----------------------------------------------------------------
        o2: OxygenDebtState = bio.oxygen_debt
        debt_inc = (1.0 - perf.overall_perf) * 5.0
        o2 = o2.with_debt(o2.debt + debt_inc)

        # -----------------------------------------------------------------
        # 5. Metabolic reserve decreases with debt
        # -----------------------------------------------------------------
        meta: MetabolicReserveState = bio.metabolic_reserve
        meta = meta.with_reserve(max(0.0, meta.reserve - o2.debt * 0.001))

        # -----------------------------------------------------------------
        # 6. Acid‑base balance reacts to oxygen debt (pH drop)
        # -----------------------------------------------------------------
        acid: AcidBaseBalanceState = bio.acid_base
        new_ph = 7.4 - (o2.debt * 0.001)
        acid = acid.with_pH(new_ph)

        # -----------------------------------------------------------------
        # 7. Tissue healing – benefits from good perfusion
        # -----------------------------------------------------------------
        heal: TissueHealingState = bio.tissue_healing
        heal_inc = (1.0 - heal.progress) * 0.01 * perf.overall_perf
        heal = heal.with_progress(heal.progress + heal_inc)

        # -----------------------------------------------------------------
        # 8. Necrosis progression – driven by ischemic regions
        # -----------------------------------------------------------------
        nec: NecrosisProgressionState = bio.necrosis
        ischemic_regions = sum(1 for r in anatomy.regions if r.ischemia)
        nec = nec.with_level(min(1.0, nec.level + ischemic_regions * 0.05))

        # -----------------------------------------------------------------
        # 9. Organ dysfunction – simple function of perfusion loss
        # -----------------------------------------------------------------
        organ: OrganDysfunctionState = bio.organ_dysfunction
        organ = organ.with_dysfunction(1.0 - perf.overall_perf)

        # -----------------------------------------------------------------
        # 10. Endocrine stress response – catecholamine surge on low MAP
        # -----------------------------------------------------------------
        endo: EndocrineStressResponseState = bio.endocrine
        if map_val < 80.0:
            endo = endo.with_catecholamine(min(1.0, endo.catecholamine + 0.1))
        else:
            endo = endo.with_catecholamine(max(0.0, endo.catecholamine - 0.05))
        endo = endo.with_stress_hormone(min(1.0, endo.stress_hormone + 0.02 * new_infl_level))

        # -----------------------------------------------------------------
        # 11. Coagulation – inflammation raises clot level; low perfusion
        #     impairs coagulation quality.
        # -----------------------------------------------------------------
        coag: CoagulationState = bio.coagulation
        clot_inc = new_infl_level * 0.05
        if perf.overall_perf < 0.5:
            coag = coag.with_coagulopathy(min(1.0, coag.coagulopathy_score + 0.05))
        coag = coag.with_clot(min(1.0, coag.clot_level + clot_inc))

        # -----------------------------------------------------------------
        # 12. Shock – derived from MAP and perfusion
        # -----------------------------------------------------------------
        shock: SystemicShockState = bio.shock
        if map_val < 80.0:
            shock_type = "hypovolemic"
            severity = min(1.0, shock.severity + 0.1)
        elif new_infl_level > 0.7:
            shock_type = "septic"
            severity = min(1.0, shock.severity + 0.08)
        else:
            shock_type = "none"
            severity = max(0.0, shock.severity - 0.05)
        shock = shock.with_type(shock_type).with_severity(severity)

        # -----------------------------------------------------------------
        # Assemble new biology state
        # -----------------------------------------------------------------
        new_bio = replace(
            bio,
            inflammatory=infl,
            immune_activation=immune,
            perfusion=perf,
            oxygen_debt=o2,
            metabolic_reserve=meta,
            acid_base=acid,
            tissue_healing=heal,
            necrosis=nec,
            organ_dysfunction=organ,
            endocrine=endo,
            coagulation=coag,
            shock=shock,
        )

        # -----------------------------------------------------------------
        # Timeline events – emit when a metric changed meaningfully
        # -----------------------------------------------------------------
        events = []
        if new_infl_level > old_infl_level:
            events.append(TimelineEvent(world.tick, "inflammatory_escalation"))
        if debt_inc > 0:
            events.append(TimelineEvent(world.tick, "oxygen_debt_increasing"))
        if clot_inc > 0:
            events.append(TimelineEvent(world.tick, "coagulation_instability"))
        if ischemic_regions > 0:
            events.append(TimelineEvent(world.tick, "tissue_necrosis_progressing"))
        if organ.dysfunction > 0:
            events.append(TimelineEvent(world.tick, "organ_cross_talk_detected"))
        if shock_type != "none":
            events.append(TimelineEvent(world.tick, "systemic_decompensation"))

        # -----------------------------------------------------------------
        # Return updated world
        # -----------------------------------------------------------------
        new_world = world.with_biology(new_bio)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
