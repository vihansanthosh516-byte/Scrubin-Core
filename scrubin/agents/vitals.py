import random

from scrubin.clinical.thresholds import ClinicalThresholds
from scrubin.core.config import ConfigLayer
from scrubin.models.types import Vitals, VitalDelta
from scrubin.patient.profile import PatientProfile, STANDARD_PATIENT, PATIENT_PROFILES
from scrubin.physiology.trajectories import VitalTrajectory, SigmoidProcedureEffect
from scrubin.physiology.homeostasis import HomeostasisModel
from scrubin.clinical.interactions import InteractionEngine


PROCEDURE_EFFECT_MAP = {
    "blood_transfusion": {"bp_systolic": 10, "spo2": 5, "heart_rate": -5},
    "intubation": {"spo2": 5, "heart_rate": -3},
    "ventilator_adjustment": {"spo2": 3},
    "central_line": {"bp_systolic": 5, "bp_diastolic": 3},
    "surgical_intervention": {"temperature": -0.4, "heart_rate": -4},
    "oxygen_therapy": {"spo2": 3, "heart_rate": -2},
    "iv_fluids": {"bp_systolic": 5, "heart_rate": -3},
    "antibiotics": {"temperature": -0.3, "heart_rate": -3},
    "vasopressors": {"bp_systolic": 15, "heart_rate": 8},
    "airway_adjuncts": {"spo2": 4, "heart_rate": -3},
    "emergency_airway": {"spo2": 8, "heart_rate": -5},
    "bag_mask": {"spo2": 4, "heart_rate": -4},
    "iron_supplement": {"spo2": 1, "heart_rate": -2},
    "positioning": {"spo2": 2, "heart_rate": -2},
    "monitor": {},
}

RECOVERY_SPREAD_TICKS = 3


class VitalsAgent:
    def __init__(self, patient_profile: PatientProfile | None = None, thresholds: ClinicalThresholds = None):
        self._patient_profile = patient_profile
        self._thresholds = thresholds or ClinicalThresholds.defaults()
        self.VITAL_RANGES = self._thresholds.vital_ranges()

    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        config = getattr(orchestrator, 'config', None) or ConfigLayer()
        self.VITAL_RANGES = config.get_vital_ranges(thresholds=self._thresholds)
        if self._patient_profile:
            patient_mods = self._patient_profile.vital_range_modifiers()
            self.VITAL_RANGES = {**self.VITAL_RANGES, **patient_mods}
            self._state = {
                k: getattr(self._patient_profile.baseline_vitals, k, sum(v) / 2)
                for k, v in self.VITAL_RANGES.items()
            }
        else:
            self._state = {k: sum(v) / 2 for k, v in self.VITAL_RANGES.items()}
        
        self._homeostasis = HomeostasisModel(
            baseline_vitals=self._state,
            recovery_rate=self._patient_profile.recovery_rate if self._patient_profile else 0.05
        )
        self._interaction_engine = InteractionEngine()
        self._active_trajectories: list[VitalTrajectory] = []
        orchestrator.register_agent("system.boot", self._on_boot)
        orchestrator.register_agent("tick", self._on_tick)
        orchestrator.register_agent("procedure", self._on_procedure)

    def _on_boot(self, event) -> None:
        print(f"[VitalsAgent] boot vitals={self._state}")

    def _on_procedure(self, event) -> None:
        procedure = event.payload.get("procedure", "")
        effects = PROCEDURE_EFFECT_MAP.get(procedure, {})
        if not effects:
            return
        tick = event.payload.get("tick", 0)
        profile = self._patient_profile or STANDARD_PATIENT
        recovery_mult = 1.0 / profile.recovery_rate if profile.recovery_rate > 0 else 1.0
        adjusted_spread = max(1, round(RECOVERY_SPREAD_TICKS * recovery_mult))
        for vital, total_delta in effects.items():
            trajectory = SigmoidProcedureEffect(
                vital=vital,
                start_tick=tick,
                duration=adjusted_spread,
                total_delta=total_delta
            )
            self._active_trajectories.append(trajectory)
        print(f"[VitalsAgent] procedure={procedure} queued trajectories for ticks {tick}-{tick+adjusted_spread}")

    def _apply_trajectories(self, tick, vitals):
        remaining = []
        for traj in self._active_trajectories:
            if traj.is_active(tick):
                delta = traj.evaluate(tick)
                key = traj.vital
                if key in vitals:
                    vitals[key] += delta
                else:
                    vitals[key] = delta
            
            if tick < traj.end_tick:
                remaining.append(traj)
        
        self._active_trajectories = remaining
        return vitals

    def _clamp_vitals(self, vitals):
        for key, (lo, hi) in self.VITAL_RANGES.items():
            if key in vitals:
                vitals[key] = max(lo, min(hi, vitals[key]))
        return vitals

    def _on_tick(self, event) -> None:
        tick = event.payload.get("tick", 0)
        profile = self._patient_profile or STANDARD_PATIENT
        
        vitals = dict(self._state)
        
        # Minor random deterministic jitter to prevent flatlines (very small)
        for key, (lo, hi) in self.VITAL_RANGES.items():
            vitals[key] += random.uniform(-0.1, 0.1)
            
        # 1. Apply Organ System Cascades
        if hasattr(self._orchestrator, 'world'):
            from scrubin.world.coupling import SystemCouplingGraph
            organ_mods = SystemCouplingGraph.evaluate_vital_influences(self._orchestrator.world)
            for key, mod in organ_mods.items():
                if key in vitals:
                    vitals[key] += mod
            
        # Apply trajectories
        vitals = self._apply_trajectories(tick, vitals)
        
        # Ask projection for active complications (need a way to get them, 
        # but for now we can read from orchestrator if we have it)
        active_comps = []
        if hasattr(self._orchestrator, 'projections'):
            for p in self._orchestrator.projections:
                if hasattr(p, 'get_snapshot'):
                    snap = p.get_snapshot()
                    if isinstance(snap, dict) and 'active_complication' in snap and snap['active_complication']:
                        active_comps.append(snap['active_complication']['complication'])
                
        # 3. Apply interaction cascades
        interaction_mods = self._interaction_engine.evaluate_vital_interactions(active_comps)
        for key, mod in interaction_mods.items():
            if key in vitals:
                vitals[key] += mod
                
        # 4. Apply homeostasis
        vitals = self._homeostasis.apply_homeostasis(vitals)
        
        # Clamp and output
        vitals = self._clamp_vitals(vitals)
        self._state = vitals
        
        # Sync to World Model
        if hasattr(self._orchestrator, 'world'):
            self._orchestrator.world.physiology.vitals = vitals
            
        self._orchestrator.submit_vitals(tick, vitals)
        print(f"[VitalsAgent] tick={tick} vitals={vitals}")
