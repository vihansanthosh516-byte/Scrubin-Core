import math
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class LyapunovResult:
    """Result of Lyapunov analysis.

    Attributes
    ----------
    exponent: float
        Estimated Lyapunov exponent.
    regime: str
        One of "STABLE", "NEUTRAL", "CHAOTIC".
    """
    exponent: float
    regime: str  # STABLE / NEUTRAL / CHAOTIC


class LyapunovAnalyzer:
    """P7-A: Estimates a Lyapunov‑like divergence from trajectory data.

    The analyzer works on two numeric state trajectories (lists of dictionaries)
    and approximates the exponential divergence rate.  It is a lightweight,
    deterministic estimator suitable for runtime analysis.
    """

    def compute_distance(self, a: Dict, b: Dict) -> float:
        """Euclidean distance over numeric fields present in both dicts.

        Non‑numeric or missing fields are ignored.
        """
        keys = set(a.keys()) & set(b.keys())
        dist_sq = 0.0
        for k in keys:
            try:
                diff = float(a[k]) - float(b[k])
                dist_sq += diff ** 2
            except Exception:
                # Skip non‑numeric entries
                continue
        return math.sqrt(dist_sq)

    def estimate_exponent(self, trajectory_1: List[Dict], trajectory_2: List[Dict]) -> float:
        """Approximate divergence rate over time.

        Parameters
        ----------
        trajectory_1, trajectory_2:
            Two state histories of equal (or similar) length.  Each entry is a
            ``dict`` of numeric state values.

        Returns
        -------
        float
            Approximate Lyapunov exponent (slope of log‑distance vs time).
        """
        n = min(len(trajectory_1), len(trajectory_2))
        if n < 2:
            return 0.0

        # Log‑distance series
        logs: List[float] = []
        for t in range(1, n):
            d = self.compute_distance(trajectory_1[t], trajectory_2[t])
            # Clamp to avoid log(0) – a tiny epsilon is sufficient
            d = max(d, 1e-9)
            logs.append(math.log(d))

        # Simple linear slope estimate (Δlog / Δt) using the first and last point
        return (logs[-1] - logs[0]) / len(logs)

    def classify(self, exponent: float) -> LyapunovResult:
        """Classify the exponent into a stability regime.

        * ``exponent < -0.01`` → ``STABLE`` (convergent)
        * ``-0.01 <= exponent <= 0.01`` → ``NEUTRAL`` (oscillatory)
        * ``exponent > 0.01`` → ``CHAOTIC`` (divergent)
        """
        if exponent < -0.01:
            regime = "STABLE"
        elif exponent > 0.01:
            regime = "CHAOTIC"
        else:
            regime = "NEUTRAL"
        return LyapunovResult(exponent=exponent, regime=regime)
