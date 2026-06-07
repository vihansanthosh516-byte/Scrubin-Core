'''Immutable dataclasses for deterministic adaptive search (Phase P.13).'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Dict, Any


@dataclass(frozen=True)
class SearchRequest:
    """User-provided request for adaptive search."""
    objective: str
    seed: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchCandidate:
    """A candidate set of parameters for a new experiment."""
    parameters: Dict[str, Any]

    def __post_init__(self):
        from dataclasses import FrozenInstanceError
        class _FrozenDict(dict):
            def __setitem__(self, key, value):
                raise FrozenInstanceError("Cannot modify frozen dict")
        object.__setattr__(self, 'parameters', _FrozenDict(self.parameters))


@dataclass(frozen=True)
class SearchRecommendation:
    """A ranked recommendation for a candidate experiment."""
    candidate: SearchCandidate
    explanation: str
    recommendation_hash: str


@dataclass(frozen=True)
class SearchHistory:
    """Immutable record of a completed experiment run."""
    experiment_id: str
    run_id: str
    replay_hash: str
    parameters: Tuple[Tuple[str, Any], ...]  # Sorted tuples for deterministic ordering
    timestamp: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class SearchMetadata:
    """Metadata attached to search results and history."""
    created_at: str
    version: str = "P.13"


@dataclass(frozen=True)
class SearchResult:
    """Result of an adaptive search operation."""
    recommendations: Tuple[SearchRecommendation, ...]
    recommendation_hash: str
    next_experiment: Any  # ExperimentDefinition – kept generic to avoid circular import
