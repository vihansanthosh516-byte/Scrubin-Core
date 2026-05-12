from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from scrubin.rl.action_space import ClinicalAction


@dataclass
class PolicyMetadata:
    policy_id: str
    version: int
    training_seed: int
    created_at: str = ""
    reward_config_hash: str = ""
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    policy_hash: str = ""
    description: str = ""
    parent_version: int = -1

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "training_seed": self.training_seed,
            "created_at": self.created_at,
            "reward_config_hash": self.reward_config_hash,
            "performance_metrics": dict(self.performance_metrics),
            "policy_hash": self.policy_hash,
            "description": self.description,
            "parent_version": self.parent_version,
        }


PolicyFn = Callable[[Any], ClinicalAction]


class PolicyRegistry:
    def __init__(self):
        self._policies: Dict[str, Dict[int, tuple[PolicyMetadata, PolicyFn]]] = {}

    def register(self, metadata: PolicyMetadata, policy_fn: PolicyFn) -> None:
        pid = metadata.policy_id
        ver = metadata.version
        if pid not in self._policies:
            self._policies[pid] = {}
        self._policies[pid][ver] = (metadata, policy_fn)

    def get(self, policy_id: str, version: int | None = None) -> Optional[tuple[PolicyMetadata, PolicyFn]]:
        versions = self._policies.get(policy_id)
        if not versions:
            return None
        if version is not None:
            return versions.get(version)
        latest = max(versions.keys())
        return versions[latest]

    def get_metadata(self, policy_id: str, version: int | None = None) -> Optional[PolicyMetadata]:
        entry = self.get(policy_id, version)
        return entry[0] if entry else None

    def get_policy_fn(self, policy_id: str, version: int | None = None) -> Optional[PolicyFn]:
        entry = self.get(policy_id, version)
        return entry[1] if entry else None

    def latest_version(self, policy_id: str) -> Optional[int]:
        versions = self._policies.get(policy_id)
        if not versions:
            return None
        return max(versions.keys())

    def list_policies(self) -> List[str]:
        return list(self._policies.keys())

    def list_versions(self, policy_id: str) -> List[int]:
        versions = self._policies.get(policy_id, {})
        return sorted(versions.keys())

    def rollback(self, policy_id: str, version: int) -> bool:
        versions = self._policies.get(policy_id)
        if not versions or version not in versions:
            return False
        to_remove = [v for v in versions if v > version]
        for v in to_remove:
            del versions[v]
        return True

    def size(self) -> int:
        return sum(len(v) for v in self._policies.values())
