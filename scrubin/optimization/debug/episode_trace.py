from typing import List
from scrubin.optimization.debug.trace_schema import EpisodeStepTrace

class EpisodeTrace:
    """
    Immutable collection of step traces for a full RL episode execution.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._steps: List[EpisodeStepTrace] = []

    def log_step(self, step_trace: EpisodeStepTrace):
        # In a real system, we'd enforce immutability or hashing here
        self._steps.append(step_trace)

    @property
    def steps(self) -> List[EpisodeStepTrace]:
        return self._steps

    def get_final_reward(self) -> float:
        return sum(s.reward for s in self._steps)
