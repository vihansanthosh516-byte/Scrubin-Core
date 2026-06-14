"""Encode a deterministic list of SurgicalEvents into an immutable Episode.

The encoder receives all events for a single simulation tick (already filtered
by tick) and the current ``SimulationWorld`` state. It extracts participants,
observations, actions, and consequences, computes an importance score, and
produces a deterministic ``Episode`` instance.
"""

from __future__ import annotations

from typing import List

from scrubin.events.event import SurgicalEvent
from scrubin.events import event_types
from scrubin.memory.episode import Episode, Observation, ActionSummary, ConsequenceSummary
from scrubin.cognition.importance import compute_importance
from scrubin.replay.hash import world_hash


def encode_events_to_episode(events: List[SurgicalEvent], world, tick: int) -> Episode:
    """Create an ``Episode`` from a list of events for ``tick``.

    Parameters
    ----------
    events:
        Deterministic ``SurgicalEvent`` objects that occurred during the tick.
    world:
        The ``SimulationWorld`` instance **after** all events have been
        processed for the tick. Used to compute the replay hash.
    tick:
        Current simulation tick.

    Returns
    -------
    Episode
        An immutable, append‑only representation of the tick.
    """
    participants_set = set()
    observations: List[Observation] = []
    actions: List[ActionSummary] = []
    consequences: List[ConsequenceSummary] = []
    event_ids: List[str] = []

    for ev in events:
        event_ids.append(ev.event_id)
        if ev.event_type == event_types.ACTION_EVENT:
            intent = ev.payload.get("intent", {})
            # Participant is the intent source (e.g., "engine", "user_action")
            source = intent.get("source")
            if source:
                participants_set.add(source)
            actions.append(
                ActionSummary(
                    name=intent.get("name", ""),
                    agent=intent.get("source", ""),
                    tick=ev.tick,
                )
            )
        elif ev.event_type == event_types.PHYSIOLOGY_EVENT:
            phys = ev.payload.get("physiology", {})
            cardio = phys.get("cardiovascular", {})
            resp = phys.get("respiratory", {})
            for name, val in cardio.items():
                observations.append(Observation(name=name, value=val, tick=ev.tick))
            for name, val in resp.items():
                observations.append(Observation(name=name, value=val, tick=ev.tick))
        elif ev.event_type == event_types.COMPLICATION_EVENT:
            comp_name = ev.payload.get("complication")
            severity_raw = ev.payload.get("severity")
            try:
                severity = float(severity_raw)
            except Exception:
                severity = None
            consequences.append(
                ConsequenceSummary(name=comp_name or "", severity=severity, tick=ev.tick)
            )
        else:
            # Other event types are ignored for episodic encoding – they are
            # either infrastructure events or already captured elsewhere.
            pass

    participants = tuple(sorted(participants_set))
    # Phase – currently a single deterministic phase string; could be extended.
    phase = "main"
    outcome = "completed"
    importance = compute_importance(events)
    replay_hash = world_hash(world)
    episode_id = f"episode-{tick}"

    return Episode(
        id=episode_id,
        tick=tick,
        phase=phase,
        participants=participants,
        observations=tuple(observations),
        actions=tuple(actions),
        consequences=tuple(consequences),
        outcome=outcome,
        importance=importance,
        event_ids=tuple(event_ids),
        replay_hash=replay_hash,
    )
