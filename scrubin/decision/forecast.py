from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import copy

@dataclass
class OrganFailureProjection:
    target_tick: int
    organ_health: dict[str, float]

@dataclass
class MortalityProjection:
    target_tick: int
    mortality_risk: float

@dataclass
class ResourceProjection:
    target_tick: int
    resource_exhaustion_risk: dict[str, float]

@dataclass
class TrajectoryForecast:
    target_tick: int
    predicted_vitals: dict[str, float]
    predicted_complications: list[str]
    organ_projection: OrganFailureProjection
    mortality_projection: MortalityProjection
    resource_projection: ResourceProjection

@dataclass
class RiskForecast:
    horizon_ticks: int
    deterioration_risk: float
    escalation_risk: float
    critical_vital_risk: dict[str, float]
    organ_failure_risk: float
    mortality_trend: float

@dataclass
class ProjectedOutcome:
    action_name: str
    target: str
    forecasts: list[TrajectoryForecast]
    overall_risk: RiskForecast
    stabilization_score: float

class Forecaster:
    def __init__(self, thresholds, interaction_engine, homeostasis_model):
        self.thresholds = thresholds
        self.interactions = interaction_engine
        self.homeostasis = homeostasis_model

    def predict_world_state(self, world, action=None, ticks_ahead: int = 5) -> TrajectoryForecast:
        """
        Projects the entire SimulationWorld forward deterministically.
        """
        # Create a light clone of the world for projection
        from scrubin.world.coupling import SystemCouplingGraph
        from scrubin.clinical.mortality import MortalityModel
        from scrubin.clinical.scoring.sofa import SOFAScore
        from scrubin.clinical.scoring.news2 import NEWS2Score
        
        sim_world = copy.deepcopy(world)
        
        for _ in range(ticks_ahead):
            from scrubin.physiology.organs.cardiovascular import CardiovascularSystem
            from scrubin.physiology.organs.respiratory import RespiratorySystem
            from scrubin.physiology.organs.renal import RenalSystem

            vitals = sim_world.physiology.vitals

            cv_sys = CardiovascularSystem()
            cv_sys.state = sim_world.organ_state.cardiovascular
            sim_world.organ_state.cardiovascular = cv_sys.evaluate(vitals)

            resp_sys = RespiratorySystem()
            resp_sys.state = sim_world.organ_state.respiratory
            sim_world.organ_state.respiratory = resp_sys.evaluate(vitals)

            renal_sys = RenalSystem()
            renal_sys.state = sim_world.organ_state.renal
            sim_world.organ_state.renal = renal_sys.evaluate(sim_world.organ_state.cardiovascular)
            
            # Cascades
            SystemCouplingGraph.apply_organ_cascades(sim_world)
            organ_mods = SystemCouplingGraph.evaluate_vital_influences(sim_world)
            for key, mod in organ_mods.items():
                if key in vitals:
                    vitals[key] += mod
            
            # Update scores and mortality
            sim_world.sofa_score = SOFAScore.calculate(vitals, {"renal": sim_world.organ_state.renal})
            sim_world.news2_score = NEWS2Score.calculate(vitals)
            sim_world.mortality_risk = MortalityModel.evaluate(sim_world)
            
        return TrajectoryForecast(
            target_tick=sim_world.tick + ticks_ahead,
            predicted_vitals=sim_world.physiology.vitals,
            predicted_complications=[], # Placeholder for complication projection
            organ_projection=OrganFailureProjection(
                target_tick=sim_world.tick + ticks_ahead,
                organ_health={
                    "cardiovascular": sim_world.organ_state.cardiovascular.health,
                    "respiratory": sim_world.organ_state.respiratory.health,
                    "renal": sim_world.organ_state.renal.health
                }
            ),
            mortality_projection=MortalityProjection(
                target_tick=sim_world.tick + ticks_ahead,
                mortality_risk=sim_world.mortality_risk
            ),
            resource_projection=ResourceProjection(
                target_tick=sim_world.tick + ticks_ahead,
                resource_exhaustion_risk={} # Compute probability of resource exhaustion
            )
        )
