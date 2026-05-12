import json
import os
from typing import Any

from scrubin.clinical.thresholds import ClinicalThresholds

_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "patch_registry.json")


DEFAULTS = {
    "agents/vitals.py": {
        "oxygenation.min_spo2": 94,
        "oxygenation.max_spo2": 100,
        "heart_rate.min": 60,
        "heart_rate.max": 100,
        "bp_systolic.min": 90,
        "bp_systolic.max": 140,
        "bp_diastolic.min": 60,
        "bp_diastolic.max": 90,
        "temperature.min": 36.1,
        "temperature.max": 37.2,
    },
    "agents/complication.py": {
        "complication_prob": 0.15,
    },
    "agents/procedure.py": {
        "procedure_trigger": "complication_gated",
    },
    "procedures.yaml": {
        "recovery_window": 5,
    },
    "core/bus.py": {
        "event_ordering": "priority_heap",
    },
}


class ConfigLayer:
    def __init__(self, registry_path: str = None, active_profile: str = "default"):
        self._registry_path = registry_path or os.path.abspath(_REGISTRY_PATH)
        self._active_profile = active_profile
        self._overrides: dict[str, dict[str, Any]] = {}
        self._filtered_entries: list[dict] = []
        self._logic_entries: list[dict] = []
        self._load_registry()

    def _load_registry(self):
        if not os.path.exists(self._registry_path):
            self._overrides = {}
            self._logic_entries = []
            return
        with open(self._registry_path, "r") as f:
            entries = json.load(f)

        self._filtered_entries = self._filter_by_scope(entries)

        for entry in self._filtered_entries:
            if entry.get("patch_type", "config") == "logic":
                continue
            target = entry["target"]
            path = entry["path"]
            value = entry["new_value"]
            self._overrides.setdefault(target, {})[path] = value

        self._logic_entries = [
            e for e in self._filtered_entries
            if e.get("patch_type", "config") == "logic"
        ]

    def _filter_by_scope(self, entries: list[dict]) -> list[dict]:
        matched = []
        seen = set()
        for entry in entries:
            scope = entry.get("scope", {"profile": "default"})
            entry_profile = scope.get("profile", "default")

            if entry_profile != self._active_profile:
                continue

            ptype = entry.get("patch_type", "config")
            dedup_key = (entry["target"], entry["path"], ptype)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            matched.append(entry)

        matched.sort(key=lambda e: e.get("priority", 0), reverse=True)
        return matched

    def get(self, target: str, path: str, fallback: Any = None) -> Any:
        if target in self._overrides and path in self._overrides[target]:
            return self._overrides[target][path]
        if target in DEFAULTS and path in DEFAULTS[target]:
            return DEFAULTS[target][path]
        return fallback

    def get_vital_ranges(self, thresholds: ClinicalThresholds = None) -> dict:
        t = thresholds or ClinicalThresholds.defaults()
        base = t.vital_ranges()
        overrides = {}
        for key in base:
            parts = key.split("_")
            config_key = key
            if key in ("spo2",):
                min_path = "oxygenation.min_spo2"
                max_path = "oxygenation.max_spo2"
            else:
                min_path = f"{key}.min"
                max_path = f"{key}.max"
            lo = self.get("agents/vitals.py", min_path, base[key][0])
            hi = self.get("agents/vitals.py", max_path, base[key][1])
            if lo != base[key][0] or hi != base[key][1]:
                overrides[key] = (lo, hi)
        if overrides:
            return {**base, **overrides}
        return base

    @property
    def registry_path(self) -> str:
        return self._registry_path

    @property
    def active_profile(self) -> str:
        return self._active_profile

    @property
    def has_overrides(self) -> bool:
        return bool(self._overrides)

    @property
    def filtered_entries(self) -> list[dict]:
        return list(self._filtered_entries)

    @property
    def logic_entries(self) -> list[dict]:
        return list(self._logic_entries)
