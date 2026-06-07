# Run diff engine – deterministic comparison of two execution artifacts.
"""
Provides a ``diff_runs`` function that compares two ``ExecutionArtifact`` objects
and identifies the first tick at which they diverge, the differing fields at
that tick, and the length of the identical prefix.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class RunDiff:
    """Result of a deterministic run comparison.

    Attributes
    ----------
    diverged_at_tick: int | None
        The tick index (0‑based) where the two runs first differ. ``None`` if the
        runs are identical for the length of the shorter trajectory.
    differing_fields: dict
        Shallow mapping of top‑level fields that differ at the divergence point.
        The value is a ``{"a": <value_from_a>, "b": <value_from_b>}`` mapping.
    identical_prefix_length: int
        Number of initial ticks (including tick 0) that are identical.
    """

    diverged_at_tick: int | None
    differing_fields: dict
    identical_prefix_length: int


def _hash_state(state: Any) -> str:
    """Deterministic hash for a state snapshot (dict‑like)."""
    data = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def _shallow_diff(a: Any, b: Any) -> dict:
    """Return a shallow diff between two dict‑like snapshots.

    The result maps each differing top‑level key to a sub‑dict ``{"a": val_a,
    "b": val_b}``.
    """
    diff: dict = {}
    if not isinstance(a, dict) or not isinstance(b, dict):
        return diff
    keys = set(a.keys()) | set(b.keys())
    for k in keys:
        av = a.get(k)
        bv = b.get(k)
        if av != bv:
            diff[k] = {"a": av, "b": bv}
    return diff


def diff_runs(run_a: Any, run_b: Any) -> RunDiff:
    """Compare two deterministic runs and return a ``RunDiff``.

    Parameters
    ----------
    run_a, run_b: ExecutionArtifact (or compatible objects)
        Objects that expose a ``trajectory`` attribute – a list of state snapshots.

    Returns
    -------
    RunDiff
        Summary of the comparison.
    """
    traj_a: List[Any] = getattr(run_a, "trajectory", [])
    traj_b: List[Any] = getattr(run_b, "trajectory", [])
    min_len = min(len(traj_a), len(traj_b))
    identical = 0
    diverged_tick: int | None = None
    diff_fields: dict = {}
    for i in range(min_len):
        if _hash_state(traj_a[i]) != _hash_state(traj_b[i]):
            diverged_tick = i
            diff_fields = _shallow_diff(traj_a[i], traj_b[i])
            break
        identical += 1
    # If no divergence within the overlapping prefix but lengths differ, treat the
    # extra ticks as a divergence at the first extra index.
    if diverged_tick is None and len(traj_a) != len(traj_b):
        diverged_tick = min_len
        # Compare the extra element (if any) against an empty dict.
        extra = traj_a[min_len] if len(traj_a) > min_len else traj_b[min_len]
        diff_fields = _shallow_diff(extra, {})
    return RunDiff(diverged_at_tick=diverged_tick, differing_fields=diff_fields, identical_prefix_length=identical)
