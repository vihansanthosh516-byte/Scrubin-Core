import math
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class Attractor:
    """Simple attractor representation.

    Attributes
    ----------
    center: Tuple[float, ...]
        The centroid of the cluster in phase space.
    radius: float
        Fixed radius used for clustering (threshold).
    size: int
        Number of points assigned to this attractor.
    """
    center: Tuple[float, ...]
    radius: float
    size: int


class PhaseSpaceAnalyzer:
    """P7‑C: Maps system trajectories into phase space and identifies structure.

    The analyzer converts a list of state dictionaries into numeric vectors,
    clusters them using a simple radius‑based method, and classifies the overall
    dynamics based on the number of attractor clusters.
    """

    # -----------------------------------------------------------------
    def embed(self, trajectory: List[Dict]) -> List[Tuple[float, ...]]:
        """Convert state dicts into numeric vectors.

        Non‑numeric fields are ignored.  Keys are sorted to ensure deterministic
        ordering across runs.
        """
        embedded: List[Tuple[float, ...]] = []
        for state in trajectory:
            vec: List[float] = []
            for k in sorted(state.keys()):
                try:
                    vec.append(float(state[k]))
                except Exception:
                    # Skip non‑numeric entries
                    continue
            embedded.append(tuple(vec))
        return embedded

    # -----------------------------------------------------------------
    @staticmethod
    def _distance(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
        """Euclidean distance between two phase‑space points."""
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    # -----------------------------------------------------------------
    def detect_attractors(
        self,
        embedded: List[Tuple[float, ...]],
        threshold: float = 0.5,
    ) -> List[Attractor]:
        """Cluster points into attractors using a fixed radius threshold.

        Parameters
        ----------
        embedded:
            List of phase‑space vectors.
        threshold:
            Distance within which a point is considered part of an existing
            attractor.
        """
        clusters: List[Attractor] = []

        for point in embedded:
            placed = False
            for cluster in clusters:
                if self._distance(point, cluster.center) < threshold:
                    # Update centroid incrementally
                    new_center = tuple(
                        (c * cluster.size + p) / (cluster.size + 1)
                        for c, p in zip(cluster.center, point)
                    )
                    cluster.center = new_center
                    cluster.size += 1
                    placed = True
                    break
            if not placed:
                clusters.append(Attractor(center=point, radius=threshold, size=1))

        return clusters

    # -----------------------------------------------------------------
    def classify(self, attractors: List[Attractor]) -> str:
        """Classify overall dynamics based on the number of attractors.

        Returns one of ``"CONVERGENT"``, ``"OSCILLATORY"`` or ``"CHAOTIC"``.
        """
        if len(attractors) == 1:
            return "CONVERGENT"
        if len(attractors) <= 3:
            return "OSCILLATORY"
        return "CHAOTIC"
