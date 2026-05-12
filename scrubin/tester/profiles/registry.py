class StressProfile:
    name: str = "default"
    vitals_override: dict = {}
    complication_prob: float = 0.15
    complication_list: list | None = None
    procedure_enabled: bool = True
    vitals_drift: float = 2.0


class HypoxiaProfile(StressProfile):
    name = "hypoxia_stress"
    vitals_override = {"spo2": (50, 75)}
    complication_list = ["hypoxia"]
    complication_prob = 0.4


class BrokenProcedureProfile(StressProfile):
    name = "broken_procedure"
    procedure_enabled = False
    complication_prob = 0.3


class CausalityRaceProfile(StressProfile):
    name = "causality_race"
    complication_prob = 0.5
    vitals_drift = 8.0


class RecoverySuppressionProfile(StressProfile):
    name = "recovery_suppression"
    procedure_enabled = False
    complication_prob = 0.25
    vitals_override = {"spo2": (80, 92)}


PROFILES = {
    "default": StressProfile,
    "hypoxia": HypoxiaProfile,
    "broken_procedure": BrokenProcedureProfile,
    "causality_race": CausalityRaceProfile,
    "recovery_suppression": RecoverySuppressionProfile,
}
