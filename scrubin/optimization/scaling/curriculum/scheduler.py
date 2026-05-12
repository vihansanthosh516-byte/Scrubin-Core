from typing import Dict, Any

class CurriculumScheduler:
    """
    Adjusts simulation difficulty based on scientific stability and performance.
    Ensures RL stays within the 'zone of proximal stability'.
    """
    def __init__(self, start_difficulty: float = 0.1):
        self.difficulty = start_difficulty

    def update(self, metrics: Dict[str, Any]):
        """
        Difficulty increases only if clinical calibration pass rates are high.
        """
        pass_rate = metrics.get("calibration_pass_rate", 0.0)
        
        if pass_rate > 0.95:
            self.difficulty += 0.05
        elif pass_rate < 0.80:
            self.difficulty -= 0.05
            
        self.difficulty = max(0.1, min(1.0, self.difficulty))
        
    def get_difficulty(self) -> float:
        return round(self.difficulty, 3)
