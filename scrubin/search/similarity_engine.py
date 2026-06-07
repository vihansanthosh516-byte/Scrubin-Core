'''Deterministic similarity/distance engine for adaptive search.'''
from __future__ import annotations

import math
from typing import Dict, Any


class SimilarityEngine:
    """Provides deterministic distance calculations between parameter vectors."""
    @staticmethod
    def _numeric(value: Any) -> bool:
        return isinstance(value, (int, float))

    @staticmethod
    def euclidean(v1: Dict[str, Any], v2: Dict[str, Any]) -> float:
        # Compute Euclidean distance over intersecting numeric keys
        total = 0.0
        for k in v1.keys() & v2.keys():
            if SimilarityEngine._numeric(v1[k]) and SimilarityEngine._numeric(v2[k]):
                diff = float(v1[k]) - float(v2[k])
                total += diff * diff
        return math.sqrt(total)

    @staticmethod
    def manhattan(v1: Dict[str, Any], v2: Dict[str, Any]) -> float:
        total = 0.0
        for k in v1.keys() & v2.keys():
            if SimilarityEngine._numeric(v1[k]) and SimilarityEngine._numeric(v2[k]):
                total += abs(float(v1[k]) - float(v2[k]))
        return total

    @staticmethod
    def exact_match(v1: Dict[str, Any], v2: Dict[str, Any]) -> float:
        return 0.0 if v1 == v2 else 1.0

    @staticmethod
    def hamming(v1: Dict[str, Any], v2: Dict[str, Any]) -> int:
        # Count differing keys (including categorical differences)
        diff = 0
        all_keys = v1.keys() | v2.keys()
        for k in all_keys:
            if v1.get(k) != v2.get(k):
                diff += 1
        return diff

    @staticmethod
    def distance(v1: Dict[str, Any], v2: Dict[str, Any], metric: str = "euclidean") -> float:
        """Dispatch to the requested metric. Available: euclidean, manhattan, exact_match, hamming."""
        if metric == "euclidean":
            return SimilarityEngine.euclidean(v1, v2)
        if metric == "manhattan":
            return SimilarityEngine.manhattan(v1, v2)
        if metric == "exact_match":
            return SimilarityEngine.exact_match(v1, v2)
        if metric == "hamming":
            return float(SimilarityEngine.hamming(v1, v2))
        raise ValueError(f"Unsupported metric: {metric}")
