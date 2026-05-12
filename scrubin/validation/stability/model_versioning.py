import hashlib
from dataclasses import dataclass
from typing import Dict

@dataclass
class ModelVersion:
    name: str
    version: str
    hash: str

class ModelVersioningSystem:
    """
    Tracks and hashes physiological model versions to link drift to changes.
    """
    def __init__(self):
        self.versions: Dict[str, ModelVersion] = {}

    def register_model(self, name: str, version: str, content: str):
        m_hash = hashlib.md5(content.encode()).hexdigest()
        self.versions[name] = ModelVersion(name, version, m_hash)

    def compare_versions(self, name: str, current_hash: str) -> bool:
        if name not in self.versions: return False
        return self.versions[name].hash == current_hash
