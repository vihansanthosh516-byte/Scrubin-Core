"""Deterministic exposure and visualization engine.

The engine deterministically progresses exposure levels, updates visualization
quality based on contamination and exposure, spreads contamination locally, and
handles occult injury revelation. All state changes are immutable – a new
``AnatomicalState`` is returned together with any ``TimelineEvent`` objects
generated during the tick.
"""

from __future__ import annotations

from typing import List, Tuple

from scrubin.world.state import TimelineEvent
from scrubin.anatomy.state import AnatomicalState, AnatomicalRegion, Injury
from scrubin.engine.random import SimulationRNG


class ExposureEngine:
    """Engine that evolves anatomical exposure, visualization, and injury.

    Parameters
    ----------
    exposure_rate: float
        Increment added to ``exposure`` each tick for structures that are being
        deliberately exposed (deterministic).  Value is capped at ``1.0``.
    visualization_decay: float
        Amount by which visualization quality degrades each tick when
        contamination interferes with a partially exposed structure.
    """

    def __init__(self, exposure_rate: float = 0.3, visualization_decay: float = 0.1):
        self.exposure_rate = exposure_rate
        self.visualization_decay = visualization_decay

    def _expose_region(self, region: AnatomicalRegion) -> Tuple[AnatomicalRegion, List[TimelineEvent]]:
        events: List[TimelineEvent] = []
        if region.exposure < 1.0:
            new_exposure = min(1.0, region.exposure + self.exposure_rate)
            region = region.with_exposure(new_exposure)
            if new_exposure >= 1.0 and not region.accessible:
                # Structure now fully exposed – mark as accessible.
                region = region.with_accessible(True)
                events.append(TimelineEvent(tick=0, description=f"structure_exposed:{region.id}"))
        return region, events

    def _update_visualization(self, region: AnatomicalRegion) -> Tuple[AnatomicalRegion, List[TimelineEvent]]:
        events: List[TimelineEvent] = []
        # Visualization degrades when contamination is present and exposure is low.
        if region.contamination and region.exposure < 0.5:
            new_quality = max(0.0, region.visualization_quality - self.visualization_decay)
            if new_quality < region.visualization_quality:
                region = region.with_visualization(new_quality)
                events.append(TimelineEvent(tick=0, description=f"visualization_lost:{region.id}"))
        return region, events

    def _reveal_occult_injuries(self, region: AnatomicalRegion, tick: int) -> Tuple[AnatomicalRegion, List[TimelineEvent]]:
        events: List[TimelineEvent] = []
        updated_injuries: List[Injury] = []
        for inj in region.injuries:
            if inj.occult and tick >= inj.onset_tick + inj.reveal_threshold:
                # Reveal the injury.
                updated_inj = inj.with_occult(False)
                updated_injuries.append(updated_inj)
                events.append(TimelineEvent(tick=tick, description=f"occult_injury_revealed:{region.id}:{inj.type}"))
            else:
                updated_injuries.append(inj)
        if updated_injuries != list(region.injuries):
            region = region.with_injuries(tuple(updated_injuries))
        return region, events

    def _spread_contamination(self, region: AnatomicalRegion, anatomy: AnatomicalState, rng: SimulationRNG) -> Tuple[AnatomicalRegion, List[TimelineEvent]]:
        events: List[TimelineEvent] = []
        if not region.contamination:
            return region, events
        # Each neighbor has a deterministic 20% chance to become contaminated.
        for neigh_id in region.neighbors:
            neighbor = anatomy.get_region(neigh_id)
            if not neighbor.contamination:
                prob = 0.2
                # Use the hidden_effects RNG stream for reproducibility.
                if rng.hidden_effects.random() < prob:
                    neighbor = neighbor.with_contamination(True)
                    events.append(TimelineEvent(tick=0, description=f"contamination_spread:{neighbor.id}"))
                    # Update anatomy state immediately – caller will replace.
                    anatomy = anatomy.with_region(neighbor)
        return region, events

    def evolve(self, anatomy: AnatomicalState, rng: SimulationRNG, tick: int) -> Tuple[AnatomicalState, List[TimelineEvent]]:
        """Evolve anatomical state for a single simulation tick.

        Returns a tuple ``(new_anatomy, events)`` where ``events`` is a list of
        ``TimelineEvent`` objects describing exposure, visualization, injury and
        contamination changes.
        """
        all_events: List[TimelineEvent] = []
        updated_regions: List[AnatomicalRegion] = []
        # First pass – deterministic exposure and visualization updates.
        for region in anatomy.regions:
            # Exposure progression.
            region, ev = self._expose_region(region)
            all_events.extend([TimelineEvent(tick=tick, description=e.description) for e in ev])
            # Visualization quality update.
            region, ev = self._update_visualization(region)
            all_events.extend([TimelineEvent(tick=tick, description=e.description) for e in ev])
            # Occult injury revelation.
            region, ev = self._reveal_occult_injuries(region, tick)
            all_events.extend([TimelineEvent(tick=tick, description=e.description) for e in ev])
            updated_regions.append(region)
        # Apply the first‑pass updates.
        anatomy = anatomy.with_updated_regions(updated_regions)
        # Second pass – contamination spread (needs the updated anatomy for neighbor lookups).
        final_regions: List[AnatomicalRegion] = []
        for region in anatomy.regions:
            region, ev = self._spread_contamination(region, anatomy, rng)
            all_events.extend([TimelineEvent(tick=tick, description=e.description) for e in ev])
            final_regions.append(region)
        anatomy = anatomy.with_updated_regions(final_regions)
        return anatomy, all_events
