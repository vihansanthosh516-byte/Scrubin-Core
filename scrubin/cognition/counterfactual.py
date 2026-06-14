"""Deterministic counterfactual data models.

The models are immutable and carry deterministic identifiers and replay hashes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple

from scrubin.events.event import SurgicalEvent
from scrubin.replay.hash import world_hash


def deterministic_counterfactual_id(source_episode_id: str, tick: int, event_id: str) -> str:
    """Deterministic ID for a counterfactual scenario.

    Hashes the tuple (source_episode_id, tick, event_id) and returns the first
    12 hex characters prefixed with ``cf-``.
    """
    canonical = json.dumps(
        {"source_episode_id": source_episode_id, "tick": tick, "event_id": event_id},
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"cf-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_counterfactual_result_id(scenario_id: str, result_hash: str) -> str:
    """Deterministic ID for a counterfactual result.

    Combines the scenario ID with the result world hash.
    """
    canonical = json.dumps({"scenario_id": scenario_id, "result_hash": result_hash}, separators=(",", ":"), sort_keys=True)
    return f"cfr-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_counterfactual_hash(data: dict) -> str:
    """Compute deterministic SHA‑256 hash of a canonical JSON representation of the dict.
    """
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class CounterfactualScenario:
    """Immutable description of a hypothetical alteration to the simulation."""
    id: str
    source_episode_id: str
    starting_tick: int
    hypothetical_event: SurgicalEvent
    confidence: float
    replay_hash: str

    @staticmethod
    def create(source_episode_id: str, starting_tick: int, hypothetical_event: SurgicalEvent, confidence: float = 1.0) -> "CounterfactualScenario":
        scenario_id = deterministic_counterfactual_id(source_episode_id, starting_tick, hypothetical_event.event_id)
        # Build placeholder; compute hash later.
        placeholder = CounterfactualScenario(
            id=scenario_id,
            source_episode_id=source_episode_id,
            starting_tick=starting_tick,
            hypothetical_event=hypothetical_event,
            confidence=confidence,
            replay_hash="",
        )
        # Compute replay hash based on fields (excluding replay_hash itself).
        hash_val = deterministic_counterfactual_hash({
            "id": placeholder.id,
            "source_episode_id": placeholder.source_episode_id,
            "starting_tick": placeholder.starting_tick,
            "event_id": placeholder.hypothetical_event.event_id,
            "confidence": placeholder.confidence,
        })
        return replace(placeholder, replay_hash=hash_val)


@dataclass(frozen=True)
class CounterfactualResult:
    """Immutable result of applying a counterfactual scenario to a world snapshot."""
    id: str
    scenario_id: str
    resulting_world_hash: str
    mortality_risk: float
    sofa_score: int
    news2_score: int
    resulting_complications: Tuple[str, ...]
    resulting_timeline: Tuple[Tuple[int, str], ...]
    confidence: float
    replay_hash: str

    @staticmethod
    def create(
        scenario: CounterfactualScenario,
        resulting_world_hash: str,
        mortality_risk: float,
        sofa_score: int,
        news2_score: int,
        resulting_complications: Tuple[str, ...],
        resulting_timeline: Tuple[Tuple[int, str], ...],
        confidence: float,
    ) -> "CounterfactualResult":
        result_id = deterministic_counterfactual_result_id(scenario.id, resulting_world_hash)
        placeholder = CounterfactualResult(
            id=result_id,
            scenario_id=scenario.id,
            resulting_world_hash=resulting_world_hash,
            mortality_risk=mortality_risk,
            sofa_score=sofa_score,
            news2_score=news2_score,
            resulting_complications=resulting_complications,
            resulting_timeline=resulting_timeline,
            confidence=confidence,
            replay_hash="",
        )
        # Compute deterministic hash for the result (excluding its own hash)
        hash_val = deterministic_counterfactual_hash({
            "id": placeholder.id,
            "scenario_id": placeholder.scenario_id,
            "resulting_world_hash": placeholder.resulting_world_hash,
            "mortality_risk": placeholder.mortality_risk,
            "sofa_score": placeholder.sofa_score,
            "news2_score": placeholder.news2_score,
            "resulting_complications": list(placeholder.resulting_complications),
            "resulting_timeline": list(placeholder.resulting_timeline),
            "confidence": placeholder.confidence,
        })
        return replace(placeholder, replay_hash=hash_val)
