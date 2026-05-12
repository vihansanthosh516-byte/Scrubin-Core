from dataclasses import dataclass
from typing import Callable, Literal

from scrubin.world.model import SimulationWorld


@dataclass(frozen=True)
class SimulationInvariant:
    id: str
    description: str
    severity: Literal["warn", "error", "fatal"]
    evaluator: Callable[[SimulationWorld], bool]
