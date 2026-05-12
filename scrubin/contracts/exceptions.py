class SimulationCorruptionError(Exception):
    pass


class InvariantFatalError(SimulationCorruptionError):
    def __init__(self, violations: list):
        msgs = "; ".join(f"{v.invariant_id}: {v.message}" for v in violations)
        super().__init__(f"Fatal invariant violations at tick {violations[0].tick}: {msgs}")
        self.violations = violations
