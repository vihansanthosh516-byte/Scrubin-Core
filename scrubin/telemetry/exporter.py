from dataclasses import dataclass
from typing import Dict, List, Any
import json

class TelemetryExporter:
    """
    Exports planner node metrics, arbitration traces, and resource pressure heatmaps.
    Crucial for debugging multi-agent conflicts and MCTS execution.
    """
    def __init__(self):
        self.arbitration_traces = []
        self.planner_metrics = []
        
    def log_arbitration(self, tick: int, recommendations: List[Any], approved: List[Any]):
        self.arbitration_traces.append({
            "tick": tick,
            "total_recommendations": len(recommendations),
            "approved_recommendations": len(approved),
            "rejected_recommendations": len(recommendations) - len(approved),
            "details": [
                {
                    "agent": rec.agent_id,
                    "action": rec.proposed_action,
                    "patient": rec.target_patient,
                    "approved": rec in approved
                } for rec in recommendations
            ]
        })
        
    def log_planner_metrics(self, tick: int, patient_id: str, planning_result: Any):
        self.planner_metrics.append({
            "tick": tick,
            "patient_id": patient_id,
            "explored_nodes": planning_result.explored_nodes,
            "search_depth": planning_result.search_depth,
            "projected_mortality": planning_result.projected_mortality,
            "confidence": planning_result.confidence
        })
        
    def export_dashboard_data(self) -> str:
        return json.dumps({
            "arbitration": self.arbitration_traces[-50:], # Last 50 ticks
            "planner": self.planner_metrics[-50:]
        }, indent=2)
