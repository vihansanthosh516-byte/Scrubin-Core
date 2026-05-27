from typing import Dict


class AttractorClassifier:
    """P6.5: Classifies the dynamical regime of a system based on metrics.

    The classification follows simple heuristic thresholds that map the
    ``stability``, ``drift`` and ``variance`` values produced by
    :class:`EquilibriumAnalyzer` onto one of four categories:

    * ``"CONVERGENT"`` – high stability, low drift/variance.
    * ``"OSCILLATORY"`` – moderate variance with low drift.
    * ``"CHAOTIC"`` – high drift, indicating rapid divergence.
    * ``"UNSTABLE"`` – fallback for any other combination.
    """

    def classify(self, metrics: Dict[str, float]) -> str:
        """Classify the system regime.

        Parameters
        ----------
        metrics:
            Dictionary containing ``stability``, ``drift`` and ``variance``.
            Missing keys default to ``0.0``.

        Returns
        -------
        str
            One of ``"CONVERGENT"``, ``"OSCILLATORY"``, ``"CHAOTIC"`` or ``"UNSTABLE"``.
        """
        stability = metrics.get("stability", 0.0)
        drift = metrics.get("drift", 0.0)
        variance = metrics.get("variance", 0.0)

        # Heuristic thresholds – chosen to be simple yet produce distinct
        # regimes for typical synthetic trajectories.
        if stability > 0.8:
            return "CONVERGENT"
        if variance > 1.0 and drift < 0.1:
            return "OSCILLATORY"
        if drift > 0.5:
            return "CHAOTIC"
        return "UNSTABLE"
