from scrubin.models.complication import (
    ComplicationDefinition,
    EscalationRule,
    ResolutionRule,
    SeverityProfile,
)
from scrubin.models.types import VitalDelta


_COMPLICATIONS: dict[str, ComplicationDefinition] = {}

_COMPLICATIONS["hemorrhage"] = ComplicationDefinition(
    id="hemorrhage",
    category="cardiovascular",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(bp_systolic=-5, heart_rate=5),
        moderate=VitalDelta(bp_systolic=-15, heart_rate=15, spo2=-3),
        severe=VitalDelta(bp_systolic=-30, heart_rate=30, spo2=-8),
    ),
    escalation=EscalationRule(next="moderate", probability=0.3),
    resolution=ResolutionRule(base_ticks=4, required_actions=("blood_transfusion",)),
)

_COMPLICATIONS["infection"] = ComplicationDefinition(
    id="infection",
    category="infectious",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(temperature=0.3, heart_rate=5),
        moderate=VitalDelta(temperature=0.8, heart_rate=12, spo2=-2),
        severe=VitalDelta(temperature=1.5, heart_rate=25, spo2=-5),
    ),
    escalation=EscalationRule(next="moderate", probability=0.25),
    resolution=ResolutionRule(base_ticks=6, required_actions=("surgical_intervention",)),
)

_COMPLICATIONS["thrombosis"] = ComplicationDefinition(
    id="thrombosis",
    category="cardiovascular",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(bp_systolic=5, heart_rate=3),
        moderate=VitalDelta(bp_systolic=12, heart_rate=10, spo2=-4),
        severe=VitalDelta(bp_systolic=25, heart_rate=20, spo2=-10),
    ),
    escalation=EscalationRule(next="moderate", probability=0.2),
    resolution=ResolutionRule(base_ticks=5, required_actions=("central_line",)),
)

_COMPLICATIONS["anemia"] = ComplicationDefinition(
    id="anemia",
    category="hematologic",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(spo2=-2, heart_rate=3),
        moderate=VitalDelta(spo2=-5, heart_rate=8, bp_systolic=-5),
        severe=VitalDelta(spo2=-10, heart_rate=15, bp_systolic=-12),
    ),
    escalation=EscalationRule(next="moderate", probability=0.2),
    resolution=ResolutionRule(base_ticks=5, required_actions=("blood_transfusion",)),
)

_COMPLICATIONS["hypotension"] = ComplicationDefinition(
    id="hypotension",
    category="cardiovascular",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(bp_systolic=-8, heart_rate=5),
        moderate=VitalDelta(bp_systolic=-18, heart_rate=12, spo2=-3),
        severe=VitalDelta(bp_systolic=-35, heart_rate=25, spo2=-8),
    ),
    escalation=EscalationRule(next="moderate", probability=0.35),
    resolution=ResolutionRule(base_ticks=4, required_actions=("central_line", "blood_transfusion")),
)

_COMPLICATIONS["hypoxia"] = ComplicationDefinition(
    id="hypoxia",
    category="respiratory",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(spo2=-4, heart_rate=5),
        moderate=VitalDelta(spo2=-10, heart_rate=12, bp_systolic=5),
        severe=VitalDelta(spo2=-20, heart_rate=25, bp_systolic=10),
    ),
    escalation=EscalationRule(next="moderate", probability=0.4),
    resolution=ResolutionRule(base_ticks=3, required_actions=("intubation", "ventilator_adjustment")),
)

# New complication definitions for Phase 7.6

# Arterial bleeding – severe cardiovascular blood loss
_COMPLICATIONS["arterial_bleeding"] = ComplicationDefinition(
    id="arterial_bleeding",
    category="cardiovascular",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(bp_systolic=-10, heart_rate=5, spo2=-1),
        moderate=VitalDelta(bp_systolic=-20, heart_rate=10, spo2=-3),
        severe=VitalDelta(bp_systolic=-35, heart_rate=20, spo2=-5),
    ),
    escalation=EscalationRule(next="moderate", probability=0.35),
    resolution=ResolutionRule(base_ticks=4, required_actions=("blood_transfusion", "surgical_intervention")),
)

# Venous bleeding – moderate blood loss, often slower
_COMPLICATIONS["venous_bleeding"] = ComplicationDefinition(
    id="venous_bleeding",
    category="cardiovascular",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(bp_systolic=-5, heart_rate=3, spo2=-0.5),
        moderate=VitalDelta(bp_systolic=-15, heart_rate=7, spo2=-2),
        severe=VitalDelta(bp_systolic=-30, heart_rate=15, spo2=-4),
    ),
    escalation=EscalationRule(next="moderate", probability=0.25),
    resolution=ResolutionRule(base_ticks=3, required_actions=("blood_transfusion",)),
)

# Bile leak – risk of infection and metabolic derangement
_COMPLICATIONS["bile_leak"] = ComplicationDefinition(
    id="bile_leak",
    category="infectious",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(temperature=0.5, heart_rate=5, spo2=-1),
        moderate=VitalDelta(temperature=1.0, heart_rate=10, spo2=-3),
        severe=VitalDelta(temperature=1.5, heart_rate=15, spo2=-5),
    ),
    escalation=EscalationRule(next="moderate", probability=0.3),
    resolution=ResolutionRule(base_ticks=5, required_actions=("antibiotics", "surgical_intervention")),
)

# Bowel perforation – severe infection risk
_COMPLICATIONS["bowel_perforation"] = ComplicationDefinition(
    id="bowel_perforation",
    category="infectious",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(temperature=0.7, heart_rate=6, spo2=-1),
        moderate=VitalDelta(temperature=1.2, heart_rate=12, spo2=-3),
        severe=VitalDelta(temperature=1.8, heart_rate=18, spo2=-6),
    ),
    escalation=EscalationRule(next="moderate", probability=0.4),
    resolution=ResolutionRule(base_ticks=6, required_actions=("surgical_intervention", "antibiotics")),
)

# Ureter injury – urinary leak, moderate physiological impact
_COMPLICATIONS["ureter_injury"] = ComplicationDefinition(
    id="ureter_injury",
    category="general",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(bp_systolic=-5, heart_rate=3),
        moderate=VitalDelta(bp_systolic=-12, heart_rate=7),
        severe=VitalDelta(bp_systolic=-25, heart_rate=15),
    ),
    escalation=EscalationRule(next="moderate", probability=0.3),
    resolution=ResolutionRule(base_ticks=4, required_actions=("surgical_intervention",)),
)

# Pneumothorax – respiratory compromise
_COMPLICATIONS["pneumothorax"] = ComplicationDefinition(
    id="pneumothorax",
    category="respiratory",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(spo2=-2),
        moderate=VitalDelta(spo2=-5, bp_systolic=-5),
        severe=VitalDelta(spo2=-10, bp_systolic=-10),
    ),
    escalation=EscalationRule(next="moderate", probability=0.3),
    resolution=ResolutionRule(base_ticks=3, required_actions=("intubation", "ventilator_adjustment")),
)

# CO₂ embolism – acute cardio‑respiratory collapse
_COMPLICATIONS["co2_embolism"] = ComplicationDefinition(
    id="co2_embolism",
    category="cardiovascular",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(spo2=-3, heart_rate=5),
        moderate=VitalDelta(spo2=-7, heart_rate=10, bp_systolic=-5),
        severe=VitalDelta(spo2=-12, heart_rate=15, bp_systolic=-15),
    ),
    escalation=EscalationRule(next="moderate", probability=0.35),
    resolution=ResolutionRule(base_ticks=4, required_actions=("ventilator_adjustment",)),
)

# Arrhythmia – irregular heart rhythm
_COMPLICATIONS["arrhythmia"] = ComplicationDefinition(
    id="arrhythmia",
    category="cardiovascular",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(heart_rate=5),
        moderate=VitalDelta(heart_rate=10, bp_systolic=-5),
        severe=VitalDelta(heart_rate=20, bp_systolic=-10),
    ),
    escalation=EscalationRule(next="moderate", probability=0.3),
    resolution=ResolutionRule(base_ticks=3, required_actions=("vasopressors",)),
)

# Equipment failure – functional loss, no direct vitals impact
_COMPLICATIONS["equipment_failure"] = ComplicationDefinition(
    id="equipment_failure",
    category="general",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(),
        moderate=VitalDelta(),
        severe=VitalDelta(),
    ),
    escalation=EscalationRule(next="moderate", probability=0.2),
    resolution=ResolutionRule(base_ticks=2, required_actions=("monitor",)),
)

# Instrument contamination – infection risk
_COMPLICATIONS["instrument_contamination"] = ComplicationDefinition(
    id="instrument_contamination",
    category="infectious",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(temperature=0.3, heart_rate=3),
        moderate=VitalDelta(temperature=0.6, heart_rate=6, spo2=-1),
        severe=VitalDelta(temperature=1.0, heart_rate=10, spo2=-3),
    ),
    escalation=EscalationRule(next="moderate", probability=0.25),
    resolution=ResolutionRule(base_ticks=3, required_actions=("antibiotics",)),
)

# Anesthetic instability – affects vitals via anesthetic depth
_COMPLICATIONS["anesthetic_instability"] = ComplicationDefinition(
    id="anesthetic_instability",
    category="general",
    severity_profiles=SeverityProfile(
        mild=VitalDelta(bp_systolic=-5, heart_rate=5),
        moderate=VitalDelta(bp_systolic=-12, heart_rate=12),
        severe=VitalDelta(bp_systolic=-20, heart_rate=20),
    ),
    escalation=EscalationRule(next="moderate", probability=0.3),
    resolution=ResolutionRule(base_ticks=3, required_actions=("monitor",)),
)

class ComplicationRegistry:
    _registry: dict[str, ComplicationDefinition] = _COMPLICATIONS

    @classmethod
    def get(cls, complication_id: str) -> ComplicationDefinition | None:
        return cls._registry.get(complication_id)

    @classmethod
    def get_all(cls) -> dict[str, ComplicationDefinition]:
        return dict(cls._registry)

    @classmethod
    def get_ids(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def get_by_category(cls, category: str) -> list[ComplicationDefinition]:
        return [d for d in cls._registry.values() if d.category == category]

    @classmethod
    def register(cls, definition: ComplicationDefinition) -> None:
        cls._registry[definition.id] = definition

    @classmethod
    def severity_profile(cls, complication_id: str, severity: str) -> VitalDelta | None:
        defn = cls.get(complication_id)
        if defn is None:
            return None
        return defn.severity_profiles.for_severity(severity)

    @classmethod
    def escalation_for(cls, complication_id: str) -> EscalationRule | None:
        defn = cls.get(complication_id)
        if defn is None:
            return None
        return defn.escalation

    @classmethod
    def resolution_for(cls, complication_id: str) -> ResolutionRule | None:
        defn = cls.get(complication_id)
        if defn is None:
            return None
        return defn.resolution
