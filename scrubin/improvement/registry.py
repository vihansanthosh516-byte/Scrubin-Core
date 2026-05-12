import json
import os
import time
from typing import Any

from scrubin.core.config import DEFAULTS, ConfigLayer


class PatchRegistry:
    def __init__(self, path: str = None):
        self._path = path or os.path.join(
            os.path.dirname(__file__), "..", "..", "patch_registry.json"
        )
        self._path = os.path.abspath(self._path)
        self._entries: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                self._entries = json.load(f)

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._entries, f, indent=2)

    def record(self, target: str, field: str, new_value: Any, reason: str,
               old_value: Any = None, scope: dict = None,
               activation_conditions: dict = None, priority: int = 0,
               patch_type: str = "config", target_path: str = "",
               action: str = ""):
        if old_value is None:
            defaults = DEFAULTS.get(target, {})
            old_value = defaults.get(field)

        entry = {
            "target": target,
            "field": field,
            "path": field,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
            "timestamp": time.time(),
            "scope": scope or {"profile": "default"},
            "activation_conditions": activation_conditions or {},
            "priority": priority,
            "patch_type": patch_type,
            "target_path": target_path,
            "action": action,
        }
        self._entries.append(entry)
        self._save()
        return entry

    def record_patches(self, patches: list):
        for patch in patches:
            old_value = self._resolve_old_value(patch.target, patch.path)
            self.record(
                target=patch.target,
                field=patch.path,
                new_value=patch.value,
                reason=patch.reason,
                old_value=old_value,
                scope=patch.scope,
                activation_conditions=patch.activation_conditions,
                priority=patch.priority,
                patch_type=patch.patch_type,
                target_path=patch.target_path,
                action=patch.action,
            )

    def _resolve_old_value(self, target: str, field: str):
        config = ConfigLayer(self._path)
        return config.get(target, field)

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)

    @property
    def path(self) -> str:
        return self._path

    def clear(self):
        self._entries = []
        self._save()
