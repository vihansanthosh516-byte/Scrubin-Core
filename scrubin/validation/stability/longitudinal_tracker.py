from typing import List, Dict, Any, Tuple

class LongitudinalRecord:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.history: List[Tuple[str, float]] = [] # (version, score)

class LongitudinalTracker:
    """
    Tracks the same benchmark over multiple runs and versions.
    """
    def __init__(self):
        self.records: Dict[str, LongitudinalRecord] = {}

    def add_record(self, case_id: str, version: str, score: float):
        if case_id not in self.records:
            self.records[case_id] = LongitudinalRecord(case_id)
        self.records[case_id].history.append((version, score))

    def get_trend(self, case_id: str) -> List[float]:
        if case_id not in self.records: return []
        return [score for _, score in self.records[case_id].history]

    def detect_regression(self, case_id: str, threshold: float = 0.05) -> bool:
        trend = self.get_trend(case_id)
        if len(trend) < 2: return False
        return trend[-1] > trend[-2] + threshold
