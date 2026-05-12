from typing import Any, Dict
from scrubin.optimization.rl.action_space import ClinicalAction

class ActionAdapter:
    """
    Translates RL actions into ScrubIn simulation events.
    """
    def encode(self, action: ClinicalAction, tick: int) -> Dict[str, Any]:
        """
        Converts a high-level ClinicalAction into a simulation payload.
        """
        return {
            "category": "PLANNER",
            "action_type": action.type,
            "target": action.target,
            "value": action.value,
            "tick": tick
        }
