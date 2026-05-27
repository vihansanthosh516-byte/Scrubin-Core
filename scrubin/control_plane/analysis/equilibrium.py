from typing import List, Dict, Any
import math


class EquilibriumAnalyzer:
    """P6.5: Measures system stability across execution trajectories.

    The analyzer takes a list of state dictionaries (each representing the
    system at a tick) and computes simple dynamical metrics that are useful for
    later attractor classification.
    """

    def compute_metrics(self, states: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute drift, variance, and a derived stability score.

        Parameters
        ----------
        states:
            List of state dictionaries. The implementation looks for an ``"energy"``
            key; if missing a default of ``1.0`` is used. ``"entropy"`` is also
            accepted but not currently used by the metric calculations.

        Returns
        -------
        Dict[str, float]
            ``{"drift": ..., "variance": ..., "stability": ...}``
        """
        if len(states) < 2:
            # Not enough data to compute meaningful dynamics – return neutral
            return {"drift": 0.0, "variance": 0.0, "stability": 1.0}

        # Extract a simple scalar "energy" from each state; this is a placeholder
        # for any monotonic quantity that reflects system magnitude.
        energies = [float(s.get("energy", 1.0)) for s in states]

        # Simple drift: average per‑tick change between first and last energy.
        total_change = abs(energies[-1] - energies[0])
        drift = total_change / (len(states) - 1)

        variance = self._variance(energies)

        # Stability is an inverse measure – higher variance or drift reduces it.
        # Adding a small epsilon prevents division by zero.
        epsilon = 1e-9
        stability = 1.0 / (1.0 + variance + drift + epsilon)

        return {"drift": drift, "variance": variance, "stability": stability}

    def _variance(self, xs: List[float]) -> float:
        """Return the population variance of ``xs``.

        This is a simple implementation without Bessel's correction because we are
        interested in the distribution of the observed trajectory rather than an
        unbiased estimator of a larger population.
        """
        if not xs:
            return 0.0
        mean = sum(xs) / len(xs)
        return sum((x - mean) ** 2 for x in xs) / len(xs)
