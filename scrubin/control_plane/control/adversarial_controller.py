from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ControlSignal:
    """Signal emitted by the adversarial controller.

    * ``stability_bias`` – a bias to shift system stability towards higher
      values (e.g., adjusting thresholds in the kernel).
    * ``adversary_scale`` – multiplicative factor to scale the intensity of
      adversarial fault injection (1.0 = no change).
    * ``damping_factor`` – factor used to damp oscillations or reduce variance.
    * ``exploration_boost`` – added pressure to encourage exploration of new
      fault strategies.
    """

    stability_bias: float = 0.0
    adversary_scale: float = 1.0
    damping_factor: float = 0.0
    exploration_boost: float = 0.0


class AdversarialController:
    """P6.6: Meta‑controller that modulates system dynamics based on equilibrium
    analysis.

    The controller receives the numeric metrics from :class:`EquilibriumAnalyzer`
    and the regime classification from :class:`AttractorClassifier`, then emits
    a :class:`ControlSignal` that downstream components (e.g., the kernel or the
    adversary ecosystem) can use to adapt their behavior.
    """

    def compute_control(self, metrics: Dict[str, float], regime: str) -> ControlSignal:
        """Compute a control signal from metrics and regime.

        Parameters
        ----------
        metrics:
            Dictionary containing ``stability``, ``drift`` and ``variance`` values.
        regime:
            String classification returned by ``AttractorClassifier`` – one of
            ``"CONVERGENT"``, ``"OSCILLATORY"``, ``"CHAOTIC"`` or ``"UNSTABLE"``.
        """
        stability = metrics.get("stability", 0.5)
        drift = metrics.get("drift", 0.0)
        variance = metrics.get("variance", 0.0)

        # Start with a neutral, no‑op signal.
        signal = ControlSignal()

        # Regime‑specific heuristics.
        if regime == "CONVERGENT":
            # System is too stable – inject a bit of stress to encourage
            # exploration.
            signal.exploration_boost = 0.3
            signal.adversary_scale = 1.2
        elif regime == "OSCILLATORY":
            # Dampen cycles and bias toward stability.
            signal.damping_factor = 0.4
            signal.stability_bias = 0.2
        elif regime == "CHAOTIC":
            # Chaotic behavior – aggressively damp and reduce adversarial pressure.
            signal.damping_factor = 0.7
            signal.adversary_scale = 0.6
            signal.stability_bias = 0.5
        else:  # UNSTABLE or unknown regime
            # Emergency stabilization.
            signal.damping_factor = 0.9
            signal.adversary_scale = 0.3
            signal.stability_bias = 0.8

        # Continuous adjustments that apply regardless of regime.
        # If stability is low, increase bias towards stability.
        signal.stability_bias += max(0.0, 0.5 - stability) * 0.5
        # Drift indicates rapid change – boost exploration slightly.
        signal.exploration_boost += drift * 0.2

        return signal
