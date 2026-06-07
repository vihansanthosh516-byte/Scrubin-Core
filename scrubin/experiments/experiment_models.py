'''Immutable dataclasses for experiment orchestration.'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, List, Optional


@dataclass(frozen=True)
class ExperimentDefinition:
    '''Definition of an experiment.

    Attributes
    ----------
    name: str
        Unique experiment name.
    seeds: Tuple[int, ...]
        Tuple of RNG seeds to use for runs.
    tick_count: int
        Number of ticks each run should execute.
    parameters: Dict[str, Tuple[Any, ...]]
        Parameter grid – mapping from parameter name to a tuple of possible values.
    metadata: Dict[str, Any]
        Arbitrary metadata attached to the experiment.
    initial_state: Dict[str, Any]
        Optional initial state dict for the isolation kernel.
    config: Dict[str, Any]
        Additional configuration passed to isolation runs.
    '''
    name: str
    seeds: Tuple[int, ...] = field(default_factory=tuple)
    tick_count: int = 0
    parameters: Dict[str, Tuple[Any, ...]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    initial_state: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentRun:
    '''A single run within an experiment.

    Attributes
    ----------
    run_id: str
        Unique identifier for the run.
    experiment_name: str
        Name of the experiment this run belongs to.
    params: Tuple[Tuple[str, Any], ...]
        Sorted tuple of (param_name, value) for deterministic ordering.
    seed: int
        RNG seed used for this run.
    status: str
        One of "queued", "running", "completed", "failed".
    artifact: Any
        ExecutionArtifact produced after run completion (or None).
    '''
    run_id: str
    experiment_name: str
    params: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)
    seed: int = 0
    status: str = "queued"
    artifact: Any = None


@dataclass(frozen=True)
class ExperimentStatus:
    '''Overall status of an experiment.'''
    total: int
    queued: int
    running: int
    completed: int
    failed: int


@dataclass(frozen=True)
class ExperimentSummary:
    '''Aggregated statistics for an experiment.'''
    experiment_name: str
    total_runs: int
    completed_runs: int
    failed_runs: int
    mean_ticks: float
    min_ticks: int
    max_ticks: int
    # Additional aggregated metrics can be added later.


@dataclass(frozen=True)
class ExperimentResult:
    '''Result of a single experiment run – alias for ExecutionArtifact.

    This dataclass mirrors the essential fields needed for dashboard display.
    '''
    run_id: str
    final_state: Any
    trajectory: List[Any]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ParameterSweep:
    '''Immutable collection of parameter combinations for an experiment.

    Attributes
    ----------
    combos: Tuple[Tuple[Tuple[str, Any], ...], ...]
        Each entry is a deterministic sorted tuple of (param_name, value).
    '''
    combos: Tuple[Tuple[Tuple[str, Any], ...], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExperimentArtifact:
    '''Container linking an experiment run to its execution artifact.

    Attributes
    ----------
    run_id: str
    artifact: Any  # ExecutionArtifact instance
    '''
    run_id: str
    artifact: Any
