"""Deterministic query utilities for ``Plan`` objects.

All ordering respects deterministic criteria: ``total_score`` (desc), then ``confidence``
(desc), then ``id`` (lexicographic)."""

from __future__ import annotations

from typing import Tuple, List

from .plan_store import PlanStore


def _sorted(plans: List) -> List:
    """Return plans sorted by score, confidence, then id (deterministic)."""
    return sorted(plans, key=lambda p: (-p.total_score, -p.confidence, p.id))


def latest(plan_store: PlanStore) -> Tuple:
    """Return the most recent plan (by ``root_tick``)."""
    if not plan_store.plans:
        return ()
    # Max root_tick, tie‑break with deterministic ordering
    max_tick = max(p.root_tick for p in plan_store.plans)
    candidates = [p for p in plan_store.plans if p.root_tick == max_tick]
    return tuple(_sorted(candidates))[0]


def best_plan(plan_store: PlanStore) -> Tuple:
    """Return the plan with the highest ``total_score`` (deterministic tie‑break)."""
    if not plan_store.plans:
        return ()
    return tuple(_sorted(list(plan_store.plans)))[0]


def by_tick(plan_store: PlanStore, tick: int) -> Tuple:
    """Return all plans whose ``root_tick`` equals ``tick`` (deterministic order)."""
    filtered = [p for p in plan_store.plans if p.root_tick == tick]
    return tuple(_sorted(filtered))


def by_score(plan_store: PlanStore, min_score: float) -> Tuple:
    """Return all plans with ``total_score`` >= ``min_score`` (deterministic order)."""
    filtered = [p for p in plan_store.plans if p.total_score >= min_score]
    return tuple(_sorted(filtered))


def top_plans(plan_store: PlanStore, n: int) -> Tuple:
    """Return the top ``n`` plans according to deterministic ordering."""
    return tuple(_sorted(list(plan_store.plans))[:n])
