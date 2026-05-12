from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class DiffReport:
    tick_delta: int
    vital_differences: List[str] = field(default_factory=list)
    organ_differences: List[str] = field(default_factory=list)
    resource_differences: List[str] = field(default_factory=list)
    divergence_score: float = 0.0

class DiffChecker:
    """
    Compares two world states to identify silent divergence.
    """
    def compare_worlds(self, world_a: Dict[str, Any], world_b: Dict[str, Any]) -> DiffReport:
        report = DiffReport(tick_delta=abs(world_a.get("tick", 0) - world_b.get("tick", 0)))
        
        # 1. Vital Check
        vitals_a = world_a.get("vitals", {})
        vitals_b = world_b.get("vitals", {})
        for key in vitals_a:
            if abs(vitals_a.get(key, 0) - vitals_b.get(key, 0)) > 5:
                report.vital_differences.append(f"{key} divergence")
        
        # 2. Organ Check
        organs_a = world_a.get("organs", {})
        organs_b = world_b.get("organs", {})
        for key in organs_a:
            if organs_a.get(key) != organs_b.get(key):
                report.organ_differences.append(f"{key} health mismatch")
                
        # 3. Resource Check
        res_a = world_a.get("resources", {})
        res_b = world_b.get("resources", {})
        for key in res_a:
            if res_a.get(key) != res_b.get(key):
                report.resource_differences.append(f"{key} resource mismatch")
                
        # Score calculation (simplified)
        report.divergence_score = (len(report.vital_differences) * 0.5 + 
                                  len(report.organ_differences) * 1.0 + 
                                  len(report.resource_differences) * 0.2)
        
        return report
