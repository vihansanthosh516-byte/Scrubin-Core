from scrubin.contracts.simulation import SimulationInvariant
from scrubin.contracts.violations import InvariantViolation
from scrubin.contracts.exceptions import InvariantFatalError
from scrubin.contracts.invariants import CANONICAL_INVARIANTS, HOSPITAL_INVARIANTS
from scrubin.world.model import SimulationWorld


class InvariantValidator:
    def __init__(self, invariants: list[SimulationInvariant] | None = None, ledger=None):
        self._invariants = invariants if invariants is not None else list(CANONICAL_INVARIANTS)
        self._ledger = ledger

    def validate(self, world) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        for inv in self._invariants:
            try:
                passed = inv.evaluator(world)
            except Exception:
                passed = False
            if not passed:
                violation = InvariantViolation(
                    invariant_id=inv.id,
                    severity=inv.severity,
                    message=inv.description,
                    tick=world.tick,
                )
                violations.append(violation)
                self._emit_ledger_event(inv, world.tick)

        fatal = [v for v in violations if v.severity == "fatal"]
        if fatal:
            raise InvariantFatalError(fatal)

        return violations

    def validate_soft(self, world) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        for inv in self._invariants:
            try:
                passed = inv.evaluator(world)
            except Exception:
                passed = False
            if not passed:
                violation = InvariantViolation(
                    invariant_id=inv.id,
                    severity=inv.severity,
                    message=inv.description,
                    tick=world.tick,
                )
                violations.append(violation)
                self._emit_ledger_event(inv, world.tick)
        return violations

    def validate_hospital(self, hospital) -> list[InvariantViolation]:
        all_invariants = list(self._invariants) + list(HOSPITAL_INVARIANTS)
        violations: list[InvariantViolation] = []
        for inv in all_invariants:
            try:
                passed = inv.evaluator(hospital)
            except Exception:
                passed = False
            if not passed:
                violation = InvariantViolation(
                    invariant_id=inv.id,
                    severity=inv.severity,
                    message=inv.description,
                    tick=hospital.tick,
                )
                violations.append(violation)
                self._emit_ledger_event(inv, hospital.tick)
        fatal = [v for v in violations if v.severity == "fatal"]
        if fatal:
            raise InvariantFatalError(fatal)
        return violations

    def _emit_ledger_event(self, inv: SimulationInvariant, tick: int) -> None:
        if self._ledger is None:
            return
        event_type = {
            "warn": "invariant_warning",
            "error": "invariant_error",
            "fatal": "simulation_corruption",
        }.get(inv.severity, "invariant_error")
        self._ledger.log(
            event_type=event_type,
            payload={"invariant_id": inv.id, "description": inv.description, "severity": inv.severity},
            tick=tick,
        )

    @property
    def invariants(self) -> list[SimulationInvariant]:
        return list(self._invariants)

    def add_invariant(self, invariant: SimulationInvariant) -> None:
        self._invariants.append(invariant)
