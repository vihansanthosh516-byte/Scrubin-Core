from dataclasses import dataclass


@dataclass
class InvariantViolation:
    invariant_id: str
    severity: str
    message: str
    tick: int
