class HomeostasisModel:
    def __init__(self, baseline_vitals: dict[str, float], recovery_rate: float = 0.05):
        self.baseline_vitals = baseline_vitals
        self.recovery_rate = recovery_rate

    def apply_homeostasis(self, current_vitals: dict[str, float]) -> dict[str, float]:
        """
        Pulls vitals back towards their baseline deterministic equilibrium.
        This provides emergent recovery rather than scripted procedure effects.
        """
        new_vitals = {}
        for vital, current_val in current_vitals.items():
            baseline = self.baseline_vitals.get(vital)
            if baseline is not None:
                # Move x% of the distance back to baseline per tick
                distance = baseline - current_val
                delta = distance * self.recovery_rate
                new_vitals[vital] = current_val + delta
            else:
                new_vitals[vital] = current_val
        return new_vitals
