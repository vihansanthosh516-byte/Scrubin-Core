from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional


class ComplicationStatus(str, Enum):
    LATENT = "latent"
    ACTIVE = "active"
    ESCALATING = "escalating"
    UNSTABLE = "unstable"
    STABILIZING = "stabilizing"
    RECOVERING = "recovering"
    RESOLVED = "resolved"
    CRITICAL = "critical"
    TERMINAL = "terminal"


@dataclass
class TransitionEvent:
    tick: int
    from_status: ComplicationStatus
    to_status: ComplicationStatus
    reason: str


class ComplicationLifecycle:
    def __init__(self, name: str, start_tick: int, initial_severity: str = "mild"):
        self.name = name
        self.severity = initial_severity
        self.status = ComplicationStatus.LATENT
        self.start_tick = start_tick
        self.last_transition_tick = start_tick
        self.history: list[TransitionEvent] = []

    def transition(self, to_status: ComplicationStatus, tick: int, reason: str):
        """Moves the complication to a new state and logs the transition."""
        if self.status == to_status:
            return
            
        event = TransitionEvent(
            tick=tick,
            from_status=self.status,
            to_status=to_status,
            reason=reason
        )
        self.history.append(event)
        self.status = to_status
        self.last_transition_tick = tick

    def evaluate(self, current_tick: int, vitals: dict, interventions: list[str]) -> Optional[TransitionEvent]:
        """
        Evaluates current conditions and determines if a transition is required.
        Returns the TransitionEvent if a transition occurred, else None.
        """
        elapsed = current_tick - self.last_transition_tick
        old_status = self.status
        
        # State Machine Logic
        if self.status == ComplicationStatus.LATENT:
            if elapsed >= 3:
                self.transition(ComplicationStatus.ACTIVE, current_tick, "latency period ended")
                
        elif self.status == ComplicationStatus.ACTIVE:
            if not interventions and elapsed >= 5:
                self.transition(ComplicationStatus.ESCALATING, current_tick, "no interventions provided")
            elif interventions:
                self.transition(ComplicationStatus.STABILIZING, current_tick, "interventions applied")
                
        elif self.status == ComplicationStatus.ESCALATING:
            if not interventions and elapsed >= 3:
                self.transition(ComplicationStatus.CRITICAL, current_tick, "continued deterioration")
            elif interventions:
                self.transition(ComplicationStatus.STABILIZING, current_tick, "interventions applied")
                
        elif self.status == ComplicationStatus.STABILIZING:
            if elapsed >= 4:
                self.transition(ComplicationStatus.RECOVERING, current_tick, "stabilization period complete")
                
        elif self.status == ComplicationStatus.RECOVERING:
            if elapsed >= 5:
                self.transition(ComplicationStatus.RESOLVED, current_tick, "recovery complete")
                
        elif self.status == ComplicationStatus.CRITICAL:
            if not interventions and elapsed >= 5:
                self.transition(ComplicationStatus.TERMINAL, current_tick, "terminal failure")
            elif interventions:
                self.transition(ComplicationStatus.UNSTABLE, current_tick, "heroic interventions applied")
                
        elif self.status == ComplicationStatus.UNSTABLE:
            if elapsed >= 3:
                # 50/50 chance to stabilize or relapse (deterministic based on tick + state hash ideally, but simplified here)
                # In a deterministic engine, we should rely on vitals state rather than random chance.
                # For now, if vitals are somewhat okay we stabilize.
                if vitals.get('spo2', 100) > 90 and vitals.get('bp_systolic', 120) > 90:
                    self.transition(ComplicationStatus.STABILIZING, current_tick, "vitals improved")
                else:
                    self.transition(ComplicationStatus.CRITICAL, current_tick, "vitals remain poor")

        if self.status != old_status:
            return self.history[-1]
        return None
