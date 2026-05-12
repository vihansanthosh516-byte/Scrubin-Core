import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TickProfile:
    tick: int
    tick_duration_ms: float = 0.0
    evolve_duration_ms: float = 0.0
    planner_duration_ms: float = 0.0
    validator_duration_ms: float = 0.0
    hash_duration_ms: float = 0.0
    snapshot_duration_ms: float = 0.0
    audit_duration_ms: float = 0.0


class TickProfiler:
    def __init__(self, ledger=None):
        self._ledger = ledger
        self._profiles: List[TickProfile] = []
        self._current: Optional[TickProfile] = None
        self._timers: Dict[str, float] = {}

    def start_tick(self, tick: int):
        self._current = TickProfile(tick=tick)
        self._timers["tick"] = time.perf_counter()

    def start_phase(self, phase: str):
        self._timers[phase] = time.perf_counter()

    def end_phase(self, phase: str):
        if phase in self._timers and self._current is not None:
            elapsed = (time.perf_counter() - self._timers[phase]) * 1000
            attr = f"{phase}_duration_ms"
            if hasattr(self._current, attr):
                setattr(self._current, attr, elapsed)

    def end_tick(self) -> TickProfile:
        if self._current is not None:
            self._current.tick_duration_ms = (time.perf_counter() - self._timers["tick"]) * 1000
            self._profiles.append(self._current)
            if self._ledger is not None:
                self._ledger.log(
                    "tick_profile",
                    {
                        "tick": self._current.tick,
                        "tick_duration_ms": round(self._current.tick_duration_ms, 3),
                        "evolve_duration_ms": round(self._current.evolve_duration_ms, 3),
                        "planner_duration_ms": round(self._current.planner_duration_ms, 3),
                        "validator_duration_ms": round(self._current.validator_duration_ms, 3),
                    },
                    tick=self._current.tick,
                )
            profile = self._current
            self._current = None
            self._timers.clear()
            return profile
        return TickProfile(tick=-1)

    @property
    def profiles(self) -> List[TickProfile]:
        return list(self._profiles)

    def latest(self) -> Optional[TickProfile]:
        return self._profiles[-1] if self._profiles else None

    def average_tick_ms(self, last_n: int = 0) -> float:
        samples = self._profiles[-last_n:] if last_n > 0 else self._profiles
        if not samples:
            return 0.0
        return sum(p.tick_duration_ms for p in samples) / len(samples)
