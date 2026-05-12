import yaml
from dataclasses import dataclass, field
from typing import Any, Optional

from scrubin.patient.profile import PatientProfile, PATIENT_PROFILES
from scrubin.models.types import Vitals
from scrubin.clinical.resources import ResourceManager, ResourceState
from scrubin.clinical.environment import OutbreakState, EnvironmentalPressure
from scrubin.world.model import SimulationWorld, PhysiologyState


@dataclass
class ScenarioComplication:
    id: str
    severity: str = "moderate"
    onset_tick: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "onset_tick": self.onset_tick,
        }


@dataclass
class ScenarioEvent:
    tick: int
    action: str
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "action": self.action,
            "params": self.params,
        }


@dataclass
class ScenarioTrigger:
    condition: str
    action: str
    params: dict = field(default_factory=dict)
    once: bool = True

    def to_dict(self) -> dict:
        return {
            "condition": self.condition,
            "action": self.action,
            "params": self.params,
            "once": self.once,
        }


@dataclass
class ScenarioResourceConfig:
    ventilators: int = 5
    icu_beds: int = 10
    blood_units: int = 20
    staff_bandwidth: int = 100

    def to_dict(self) -> dict:
        return {
            "ventilators": self.ventilators,
            "icu_beds": self.icu_beds,
            "blood_units": self.blood_units,
            "staff_bandwidth": self.staff_bandwidth,
        }


@dataclass
class ScenarioOutbreak:
    type: str
    severity: str = "moderate"

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
        }


@dataclass
class ScenarioPatientConfig:
    profile: str = "standard"
    initial_conditions: dict[str, float] = field(default_factory=dict)
    complications: list[ScenarioComplication] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    recovery_rate: float = 1.0
    deterioration_rate: float = 1.0

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "initial_conditions": self.initial_conditions,
            "complications": [c.to_dict() for c in self.complications],
            "risk_factors": self.risk_factors,
            "recovery_rate": self.recovery_rate,
            "deterioration_rate": self.deterioration_rate,
        }


@dataclass
class ScenarioHospitalConfig:
    ventilators: int = 5
    icu_beds: int = 10
    blood_units: int = 20
    staff_bandwidth: int = 100
    icu_beds_used: int = 8
    blood_units_used: int = 5
    staff_bandwidth_used: int = 40
    outbreak: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ventilators": self.ventilators,
            "icu_beds": self.icu_beds,
            "blood_units": self.blood_units,
            "staff_bandwidth": self.staff_bandwidth,
            "icu_beds_used": self.icu_beds_used,
            "blood_units_used": self.blood_units_used,
            "staff_bandwidth_used": self.staff_bandwidth_used,
            "outbreak": dict(self.outbreak),
        }


@dataclass
class ScenarioConfig:
    name: str
    description: str = ""
    seed: int = 0
    max_ticks: int = 200
    patient: ScenarioPatientConfig = field(default_factory=ScenarioPatientConfig)
    hospital: ScenarioHospitalConfig = field(default_factory=ScenarioHospitalConfig)
    events: list[ScenarioEvent] = field(default_factory=list)
    triggers: list[ScenarioTrigger] = field(default_factory=list)
    mode: str = "autonomous"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "seed": self.seed,
            "max_ticks": self.max_ticks,
            "patient": self.patient.to_dict(),
            "hospital": self.hospital.to_dict(),
            "events": [e.to_dict() for e in self.events],
            "triggers": [t.to_dict() for t in self.triggers],
            "mode": self.mode,
            "tags": list(self.tags),
        }


def _parse_complications(raw: list) -> list[ScenarioComplication]:
    result = []
    for c in raw:
        if isinstance(c, str):
            result.append(ScenarioComplication(id=c))
        elif isinstance(c, dict):
            result.append(ScenarioComplication(
                id=c.get("id", c.get("name", "unknown")),
                severity=c.get("severity", "moderate"),
                onset_tick=c.get("onset_tick", 0),
            ))
    return result


def _parse_patient(raw: dict) -> ScenarioPatientConfig:
    if not raw:
        return ScenarioPatientConfig()
    complications = _parse_complications(raw.get("complications", []))
    initial_conditions = {}
    for k, v in raw.get("initial_conditions", {}).items():
        initial_conditions[k] = float(v)
    return ScenarioPatientConfig(
        profile=raw.get("profile", "standard"),
        initial_conditions=initial_conditions,
        complications=complications,
        risk_factors=raw.get("risk_factors", []),
        recovery_rate=float(raw.get("recovery_rate", 1.0)),
        deterioration_rate=float(raw.get("deterioration_rate", 1.0)),
    )


def _parse_hospital(raw: dict) -> ScenarioHospitalConfig:
    if not raw:
        return ScenarioHospitalConfig()
    return ScenarioHospitalConfig(
        ventilators=int(raw.get("ventilators", 5)),
        icu_beds=int(raw.get("icu_beds", 10)),
        blood_units=int(raw.get("blood_units", 20)),
        staff_bandwidth=int(raw.get("staff_bandwidth", 100)),
        icu_beds_used=int(raw.get("icu_beds_used", raw.get("icu_beds_initial_used", 8))),
        blood_units_used=int(raw.get("blood_units_used", raw.get("blood_units_initial_used", 5))),
        staff_bandwidth_used=int(raw.get("staff_bandwidth_used", raw.get("staff_bandwidth_initial_used", 40))),
        outbreak=raw.get("outbreak", {}),
    )


def _parse_events(raw: list) -> list[ScenarioEvent]:
    result = []
    for e in raw:
        result.append(ScenarioEvent(
            tick=int(e.get("tick", 0)),
            action=e.get("action", "none"),
            params=e.get("params", {}),
        ))
    return result


def _parse_triggers(raw: list) -> list[ScenarioTrigger]:
    result = []
    for t in raw:
        result.append(ScenarioTrigger(
            condition=t.get("condition", "False"),
            action=t.get("action", "none"),
            params=t.get("params", {}),
            once=t.get("once", True),
        ))
    return result


class ScenarioParser:
    def parse(self, source: str | dict) -> ScenarioConfig:
        if isinstance(source, str):
            data = yaml.safe_load(source)
        else:
            data = source
        scenario = data.get("scenario", data)
        patient = _parse_patient(scenario.get("patient", {}))
        hospital = _parse_hospital(scenario.get("hospital", {}))
        events = _parse_events(scenario.get("events", []))
        triggers = _parse_triggers(scenario.get("triggers", []))
        return ScenarioConfig(
            name=scenario.get("name", "unnamed"),
            description=scenario.get("description", ""),
            seed=int(scenario.get("seed", 0)),
            max_ticks=int(scenario.get("max_ticks", 200)),
            patient=patient,
            hospital=hospital,
            events=events,
            triggers=triggers,
            mode=scenario.get("mode", "autonomous"),
            tags=scenario.get("tags", []),
        )


class ScenarioCompiler:
    def compile(self, config: ScenarioConfig) -> dict:
        patient_profile = self._build_patient_profile(config)
        resource_manager = self._build_resource_manager(config)
        outbreak_state = self._build_outbreak_state(config)
        initial_vitals = self._build_initial_vitals(config, patient_profile)
        return {
            "patient_profile": patient_profile,
            "resource_manager": resource_manager,
            "outbreak_state": outbreak_state,
            "initial_vitals": initial_vitals,
            "events": [e.to_dict() for e in config.events],
            "triggers": [t.to_dict() for t in config.triggers],
            "seed": config.seed,
            "max_ticks": config.max_ticks,
            "mode": config.mode,
            "scenario_name": config.name,
        }

    def compile_world(self, config: ScenarioConfig) -> SimulationWorld:
        compiled = self.compile(config)
        world = SimulationWorld()
        world.physiology.vitals = compiled["initial_vitals"]
        world.resource_manager = compiled["resource_manager"]
        return world

    def _build_patient_profile(self, config: ScenarioConfig) -> PatientProfile:
        base = PATIENT_PROFILES.get(config.patient.profile)
        if base is None:
            base = PATIENT_PROFILES["standard"]
        baseline = base.baseline_vitals
        for k, v in config.patient.initial_conditions.items():
            if hasattr(baseline, k):
                baseline = baseline.__class__(**{**baseline.to_dict(), k: v})
        complication_prob = {}
        for c in config.patient.complications:
            complication_prob[c.id] = 1.5
        return PatientProfile(
            id=config.patient.profile,
            age=base.age,
            weight=base.weight,
            baseline_vitals=baseline,
            risk_factors=tuple(config.patient.risk_factors) or base.risk_factors,
            complication_probability=complication_prob or base.complication_probability,
            recovery_rate=config.patient.recovery_rate,
            deterioration_rate=config.patient.deterioration_rate,
        )

    def _build_resource_manager(self, config: ScenarioConfig) -> ResourceManager:
        rm = ResourceManager()
        h = config.hospital
        rm.resources["ventilators"] = ResourceState(
            total_capacity=h.ventilators, currently_used=0,
        )
        rm.resources["icu_beds"] = ResourceState(
            total_capacity=h.icu_beds, currently_used=h.icu_beds_used,
        )
        rm.resources["blood_units"] = ResourceState(
            total_capacity=h.blood_units, currently_used=h.blood_units_used,
        )
        rm.resources["staff_bandwidth"] = ResourceState(
            total_capacity=h.staff_bandwidth, currently_used=h.staff_bandwidth_used,
        )
        return rm

    def _build_outbreak_state(self, config: ScenarioConfig) -> OutbreakState:
        pressures = {}
        for outbreak_type, severity in config.hospital.outbreak.items():
            key = f"{outbreak_type}_outbreak" if "outbreak" not in outbreak_type else outbreak_type
            pressures[key] = EnvironmentalPressure(
                type=outbreak_type,
                severity={"low": 0.3, "moderate": 0.6, "high": 0.9}.get(severity, 0.6),
            )
        return OutbreakState(active_pressures=pressures)

    def _build_initial_vitals(self, config: ScenarioConfig, profile: PatientProfile) -> dict:
        vitals = profile.baseline_vitals.to_dict()
        for k, v in config.patient.initial_conditions.items():
            vitals[k] = v
        return vitals


class ScenarioSerializer:
    def to_yaml(self, config: ScenarioConfig) -> str:
        data = {
            "scenario": {
                "name": config.name,
                "description": config.description,
                "seed": config.seed,
                "max_ticks": config.max_ticks,
                "mode": config.mode,
                "tags": config.tags,
                "patient": {
                    "profile": config.patient.profile,
                    "initial_conditions": config.patient.initial_conditions,
                    "complications": [c.to_dict() for c in config.patient.complications],
                    "risk_factors": config.patient.risk_factors,
                    "recovery_rate": config.patient.recovery_rate,
                    "deterioration_rate": config.patient.deterioration_rate,
                },
                "hospital": config.hospital.to_dict(),
                "events": [e.to_dict() for e in config.events],
                "triggers": [t.to_dict() for t in config.triggers],
            }
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


class ScenarioValidator:
    def validate(self, config: ScenarioConfig) -> list[str]:
        errors = []
        if not config.name:
            errors.append("Scenario name is required")
        if config.max_ticks <= 0:
            errors.append("max_ticks must be positive")
        
        # Patient validation
        if not config.patient.profile:
            errors.append("Patient profile is required")
        
        # Event validation
        for i, event in enumerate(config.events):
            if event.tick < 0:
                errors.append(f"Event {i} has negative tick: {event.tick}")
            if event.tick > config.max_ticks:
                errors.append(f"Event {i} tick {event.tick} exceeds max_ticks {config.max_ticks}")
            if not event.action:
                errors.append(f"Event {i} has no action")

        # Trigger validation
        for i, trigger in enumerate(config.triggers):
            if not trigger.condition:
                errors.append(f"Trigger {i} has no condition")
            if not trigger.action:
                errors.append(f"Trigger {i} has no action")

        return errors


class ScenarioRegistry:
    _scenarios: dict[str, ScenarioConfig] = {}

    @classmethod
    def register(cls, config: ScenarioConfig) -> None:
        cls._scenarios[config.name] = config

    @classmethod
    def get(cls, name: str) -> Optional[ScenarioConfig]:
        return cls._scenarios.get(name)

    @classmethod
    def get_all(cls) -> dict[str, ScenarioConfig]:
        return dict(cls._scenarios)

    @classmethod
    def list_names(cls) -> list[str]:
        return list(cls._scenarios.keys())

    @classmethod
    def load_from_yaml(cls, yaml_source: str | dict, name: str | None = None) -> ScenarioConfig:
        parser = ScenarioParser()
        config = parser.parse(yaml_source)
        if name is not None:
            config.name = name
        cls.register(config)
        return config


SEPTIC_SHOCK_YAML = """
scenario:
  name: septic_shock
  description: Septic shock with multi-organ dysfunction
  seed: 42
  max_ticks: 150
  tags: [sepsis, shock, benchmark]
  patient:
    profile: elderly_high_risk
    initial_conditions:
      spo2: 88
      bp_systolic: 75
      temperature: 39.2
      heart_rate: 120
    complications:
      - id: infection
        severity: severe
      - id: hypotension
        severity: severe
    risk_factors: [hypertension, diabetes]
  hospital:
    ventilators: 2
    icu_beds: 3
    icu_beds_used: 2
    blood_units: 10
    staff_bandwidth: 80
    staff_bandwidth_used: 50
"""

ARDS_YAML = """
scenario:
  name: ards
  description: Acute respiratory distress syndrome
  seed: 17
  max_ticks: 200
  tags: [respiratory, ards, benchmark]
  patient:
    profile: chronic_copd
    initial_conditions:
      spo2: 82
      respiratory_rate: 32
      heart_rate: 110
    complications:
      - id: hypoxia
        severity: severe
    risk_factors: [copd, smoker]
  hospital:
    ventilators: 1
    icu_beds: 2
    blood_units: 8
    staff_bandwidth: 60
"""

HEMORRHAGIC_TRAUMA_YAML = """
scenario:
  name: hemorrhagic_trauma
  description: Hemorrhagic trauma with cardiovascular collapse
  seed: 99
  max_ticks: 100
  tags: [trauma, hemorrhage, benchmark]
  patient:
    profile: young_healthy
    initial_conditions:
      spo2: 85
      bp_systolic: 74
      heart_rate: 130
    complications:
      - id: hemorrhage
        severity: severe
      - id: hypotension
        severity: severe
  hospital:
    ventilators: 3
    icu_beds: 5
    blood_units: 4
    staff_bandwidth: 90
"""

POST_OP_INSTABILITY_YAML = """
scenario:
  name: post_op_instability
  description: Post-operative hemodynamic instability
  seed: 55
  max_ticks: 120
  tags: [postoperative, instability, benchmark]
  patient:
    profile: elderly_high_risk
    initial_conditions:
      spo2: 90
      bp_systolic: 82
      temperature: 37.8
      heart_rate: 105
    complications:
      - id: hypotension
        severity: moderate
      - id: infection
        severity: moderate
    risk_factors: [hypertension, diabetes]
  hospital:
    ventilators: 4
    icu_beds: 6
    icu_beds_used: 4
    blood_units: 15
    staff_bandwidth: 70
    staff_bandwidth_used: 55
"""

VENTILATOR_SCARCITY_YAML = """
scenario:
  name: ventilator_scarcity
  description: Resource-constrained environment with ventilator shortage
  seed: 33
  max_ticks: 180
  tags: [resource, scarcity, triage, benchmark]
  patient:
    profile: chronic_copd
    initial_conditions:
      spo2: 80
      heart_rate: 115
    complications:
      - id: hypoxia
        severity: severe
      - id: thrombosis
        severity: moderate
  hospital:
    ventilators: 1
    icu_beds: 10
    icu_beds_used: 9
    blood_units: 20
    staff_bandwidth: 50
    staff_bandwidth_used: 48
"""

OUTBREAK_TRIAGE_YAML = """
scenario:
  name: outbreak_triage
  description: MRSA outbreak with infection control pressure
  seed: 77
  max_ticks: 200
  tags: [outbreak, infection, triage, benchmark]
  patient:
    profile: elderly_high_risk
    initial_conditions:
      spo2: 91
      temperature: 38.5
      heart_rate: 100
    complications:
      - id: infection
        severity: moderate
      - id: anemia
        severity: mild
    risk_factors: [hypertension]
  hospital:
    ventilators: 3
    icu_beds: 4
    blood_units: 6
    staff_bandwidth: 40
    staff_bandwidth_used: 38
    outbreak:
      mrsa: moderate
"""

CASCADE_FAILURE_YAML = """
scenario:
  name: cascade_failure
  description: Cascade failure starting with hemorrhage, then staff shortage, then ventilator failure
  seed: 123
  max_ticks: 300
  tags: [benchmark, cascade, stress_test]
  patient:
    profile: elderly_high_risk
    initial_conditions:
      spo2: 92
      bp_systolic: 95
  events:
    - tick: 20
      action: hemorrhage
      params: {severity: severe}
    - tick: 50
      action: staff_reduction
      params: {amount: 30}
  triggers:
    - condition: bp_systolic < 70
      action: ventilator_failure
      params: {duration: 30}
"""

CANONICAL_SCENARIOS = [
    SEPTIC_SHOCK_YAML,
    ARDS_YAML,
    HEMORRHAGIC_TRAUMA_YAML,
    POST_OP_INSTABILITY_YAML,
    VENTILATOR_SCARCITY_YAML,
    OUTBREAK_TRIAGE_YAML,
    CASCADE_FAILURE_YAML,
]


def register_canonical_scenarios() -> None:
    for yaml_source in CANONICAL_SCENARIOS:
        ScenarioRegistry.load_from_yaml(yaml_source)
