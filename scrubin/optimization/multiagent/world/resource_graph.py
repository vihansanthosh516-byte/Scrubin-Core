from typing import Dict, Any

class ResourceGraph:
    """
    Hospital realism layer: Tracks and allocates finite clinical resources.
    Enables emergent competition dynamics between agents.
    """
    def __init__(self):
        self.resources = {
            "ventilator": 5,
            "icu_bed": 10,
            "ecmo": 2,
            "staff": 20
        }

    def can_allocate(self, resource_type: str, count: int = 1) -> bool:
        return self.resources.get(resource_type, 0) >= count

    def allocate(self, resource_type: str, count: int = 1) -> bool:
        if self.can_allocate(resource_type, count):
            self.resources[resource_type] -= count
            return True
        return False

    def release(self, resource_type: str, count: int = 1):
        if resource_type in self.resources:
            self.resources[resource_type] += count
