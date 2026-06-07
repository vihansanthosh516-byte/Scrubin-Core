'''Immutable dataclasses representing dashboard entities.

All dataclasses are frozen to enforce immutability and guarantee deterministic
behaviour across the visualization layer.
'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class DashboardRunSummary:
    '''Summary information for a stored run.

    Attributes
    ----------
    run_id: str
        Unique identifier of the run.
    seed: int
        RNG seed used for the simulation.
    ticks: int
        Number of ticks recorded in the run.
    hash: str
        Deterministic hash of the final world state.
    '''
    run_id: str
    seed: int
    ticks: int
    hash: str


@dataclass(frozen=True)
class DashboardReplayFrame:
    '''A single deterministic frame of a replay.

    Attributes
    ----------
    tick: int
        Simulation tick.
    state_hash: str
        Deterministic hash of the world state at this tick.
    diff_from_previous: Dict[str, Any]
        Shallow diff of this state compared to the prior tick.
    '''
    tick: int
    state_hash: str
    diff_from_previous: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DashboardMetricSeries:
    '''Series of metric values for a run.

    name – metric name (e.g., 'event_count').
    values – ordered list of metric values per tick.
    '''
    name: str
    values: List[Any] = field(default_factory=list)


@dataclass(frozen=True)
class DashboardKnowledgeGraph:
    '''Immutable representation of a knowledge graph.

    nodes – list of node dictionaries (id, label, confidence, ...).
    edges – list of edge dictionaries (source, target, label, ...).
    '''
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class DashboardSnapshot:
    '''Snapshot of a world state with optional diff.

    Attributes
    ----------
    world_state: Dict[str, Any]
        The full world state snapshot.
    diff_from_previous: Dict[str, Any]
        Shallow diff against the previous snapshot (empty for the first).
    '''
    world_state: Dict[str, Any]
    diff_from_previous: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DashboardComparison:
    '''Result of comparing two runs.

    Attributes
    ----------
    diverged_at_tick: int | None
        First tick where runs differ, None if identical.
    identical_prefix_length: int
        Number of initial ticks that are identical.
    differing_fields: Dict[str, Any]
        Shallow diff of top-level fields at the divergence point.
    '''
    diverged_at_tick: Optional[int]
    identical_prefix_length: int
    differing_fields: Dict[str, Any] = field(default_factory=dict)
