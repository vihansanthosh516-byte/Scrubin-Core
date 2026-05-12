import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from scrubin.core.orchestrator import Orchestrator
from scrubin.scenarios.dsl import ScenarioConfig


@dataclass
class Interruption:
    type: str  # 'nurse_call', 'pager', 'equipment_glitch'
    message: str
    urgency: float  # 0.0 to 1.0
    options: List[str] = field(default_factory=list)


class TraineeSession:
    def __init__(self, trainee_id: str, orchestrator: Orchestrator, scenario_config: ScenarioConfig):
        self.session_id = f"sess-{int(time.time())}"
        self.trainee_id = trainee_id
        self.orchestrator = orchestrator
        self.scenario_config = scenario_config
        
        self.start_time = time.time()
        self.tick_times: Dict[int, float] = {}
        self.active_interruptions: List[Interruption] = []
        
        # Difficulty settings
        self.pressure_multiplier = 1.0
        self.interruptions_enabled = True
        self.partial_observability = True
        
        self._rng = random.Random(seed=orchestrator.seed)

    def process_tick(self, tick: int):
        """
        Inject training-specific effects for the current tick.
        """
        self.tick_times[tick] = time.time()
        
        if self.interruptions_enabled:
            self._maybe_trigger_interruption(tick)
            
    def _maybe_trigger_interruption(self, tick: int):
        """
        Randomly inject stressors to simulate ICU environment load.
        """
        if self._rng.random() < (0.05 * self.pressure_multiplier):
            interruption = Interruption(
                type="nurse_call",
                message="Nurse: 'Patient in Room 4 is desaturating. Can you check the vent settings?'",
                urgency=0.7,
                options=["Acknowledge", "Prioritize Room 4", "Stay with current patient"]
            )
            self.active_interruptions.append(interruption)
            self.orchestrator.bus.publish("trainee_interruption", interruption.__dict__)

        if self._rng.random() < (0.03 * self.pressure_multiplier):
            interruption = Interruption(
                type="pager",
                message="PAGER: [STAT] ER arrival - multi-trauma incoming. Expected in 5 mins.",
                urgency=0.9
            )
            self.active_interruptions.append(interruption)
            self.orchestrator.bus.publish("trainee_interruption", interruption.__dict__)

    def get_decision_pressure(self) -> float:
        """
        Returns a value from 0-1 representing the current 'stress' level.
        Based on active interruptions and physiological instability.
        """
        instability = self.orchestrator.world.instability_index
        interruption_pressure = len(self.active_interruptions) * 0.2
        return min(1.0, instability + interruption_pressure)

    def resolve_interruption(self, index: int):
        if 0 <= index < len(self.active_interruptions):
            self.active_interruptions.pop(index)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "trainee_id": self.trainee_id,
            "pressure_level": round(self.get_decision_pressure(), 6),
            "interruptions": [i.__dict__ for i in self.active_interruptions],
            "mode": self.orchestrator.mode,
            "ticks_elapsed": self.orchestrator.tick_count,
        }
