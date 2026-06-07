'''Pareto engine – deterministic non‑dominated frontier computation (Phase P.14).'''
from __future__ import annotations

from typing import List, Tuple

from .optimization_models import ParetoPoint, ParetoFront


class ParetoEngine:
    """Computes Pareto‑optimal fronts and layers deterministically."""

    @staticmethod
    def _dominates(p1: ParetoPoint, p2: ParetoPoint, directions: List[str]) -> bool:
        """Return True if ``p1`` dominates ``p2`` according to ``directions``.

        ``directions`` is a list parallel to the score tuple where each entry is either
        ``"minimize"`` or ``"maximize"``. ``p1`` dominates ``p2`` if it is no worse on all
        objectives and strictly better on at least one.
        """
        strictly_better = False
        for s1, s2, dir in zip(p1.scores, p2.scores, directions):
            v1 = s1.score
            v2 = s2.score
            if dir == "minimize":
                if v1 > v2:
                    return False
                if v1 < v2:
                    strictly_better = True
            else:  # maximize
                if v1 < v2:
                    return False
                if v1 > v2:
                    strictly_better = True
        return strictly_better

    @staticmethod
    def compute_front(points: List[ParetoPoint], directions: List[str]) -> ParetoFront:
        """Return the Pareto front (non‑dominated points) preserving input order.

        The algorithm iterates over ``points`` in the given order and keeps a list of
        current frontier points. When a new point dominates an existing frontier point,
        the dominated point is removed. If the new point is dominated, it is discarded.
        This yields deterministic results given deterministic ``points`` order.
        """
        front: List[ParetoPoint] = []
        for pt in points:
            if any(ParetoEngine._dominates(existing, pt, directions) for existing in front):
                continue
            front = [existing for existing in front if not ParetoEngine._dominates(pt, existing, directions)]
            front.append(pt)
        return ParetoFront(points=tuple(front))

    @staticmethod
    def rank_by_layers(points: List[ParetoPoint], directions: List[str]) -> List[Tuple[ParetoPoint, int]]:
        """Assign Pareto layer ranks (1 = first front, 2 = second, …) deterministically.

        The algorithm repeatedly extracts the current Pareto front, assigns the next
        rank to those points, removes them, and continues until all points are ranked.
        The order of points within a layer follows the original ``points`` order.
        """
        remaining = list(points)
        rankings: List[Tuple[ParetoPoint, int]] = []
        rank = 1
        while remaining:
            front = ParetoEngine.compute_front(remaining, directions)
            front_set = set(front.points)
            for pt in points:
                if pt in front_set:
                    rankings.append((pt, rank))
            remaining = [pt for pt in remaining if pt not in front_set]
            rank += 1
        return rankings
