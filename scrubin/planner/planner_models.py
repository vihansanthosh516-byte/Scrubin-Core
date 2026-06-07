'''Immutable dataclasses for deterministic experiment planning (Phase P.12).'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Any, Dict

@dataclass(frozen=True)
class PlanningRequest:
    """User-provided planning request."""
    objective: str
    seed: int
    initial_state: Dict[str, Any] = field(default_factory=dict)
    constraints: Tuple['PlannerConstraint', ...] = field(default_factory=tuple)
    max_runs: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Hypothesis:
    """Simple textual hypothesis."""
    description: str

@dataclass(frozen=True)
class ParameterRange:
    """Parameter name and allowed values."""
    name: str
    values: Tuple[Any, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class PlannerConstraint:
    """Constraint with type and parameters."""
    type: str
    parameters: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class PlannerMetadata:
    """Metadata for planning result."""
    created_at: str
    version: str = "P.12"

@dataclass(frozen=True)
class PlanningResult:
    """Result containing experiment definition and supporting data."""
    experiment_definition: 'scrubin.experiments.experiment_models.ExperimentDefinition'
    hypotheses: Tuple[Hypothesis, ...]
    parameter_summary: Dict[str, int]
    estimated_run_count: int
    planning_hash: str
    metadata: PlannerMetadata
