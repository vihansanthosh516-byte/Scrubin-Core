from dataclasses import dataclass, field
from typing import Any


@dataclass
class Patch:
    target: str
    action: str
    path: str
    value: Any
    reason: str
    scope: dict = field(default_factory=lambda: {"profile": "default"})
    activation_conditions: dict = field(default_factory=dict)
    priority: int = 0
    patch_type: str = "config"
    target_path: str = ""
