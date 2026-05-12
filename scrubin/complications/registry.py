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
