'''Immutable dataclasses for deterministic multi‑objective optimization (Phase P.14).'''
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any


@dataclass(frozen=True)
class OptimizationRequest:
    """User‑provided request for deterministic optimization analysis."""
    experiment_id: str
    objectives: Tuple[str, ...] = ()  # e.g., (\"maximize_map\", \"minimize_blood_loss\")
    constraints: Tuple[Any, ...] = ()
    seed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectiveDefinition:
    """Definition of a single objective – name, direction, optional weight."""
    name: str
    direction: str  # \"maximize\" or \"minimize\"
    weight: float = 1.0


@dataclass(frozen=True)
class ObjectiveScore:
    """Score of a specific objective for an experiment."""
    name: str
    score: float


@dataclass(frozen=True)
class ParetoPoint:
    """A candidate point in objective space with its associated experiment data."""
    experiment_id: str
    parameters: Tuple[Tuple[str, Any], ...]  # same format as SearchHistory.parameters
    scores: Tuple[ObjectiveScore, ...]  # ordered as in the request.objectives


@dataclass(frozen=True)
class ParetoFront:
    """Immutable collection of Pareto‑optimal points."""
    points: Tuple[ParetoPoint, ...]


@dataclass(frozen=True)
class OptimizationMetadata:
    """Metadata attached to an optimization result (deterministic)."""
    created_at: str
    version: str = "P.14"


@dataclass(frozen=True)
class OptimizationResult:
    """Result of a deterministic multi‑objective optimization run."""
    request: OptimizationRequest
    overall_hash: str
    pareto_front: ParetoFront
    rankings: Tuple[Tuple[str, int], ...]  # (experiment_id, rank) sequence
    metadata: OptimizationMetadata
