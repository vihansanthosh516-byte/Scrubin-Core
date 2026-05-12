from dataclasses import dataclass
from typing import Dict

@dataclass
class ResourceState:
    total_capacity: int
    currently_used: int

    @property
    def available(self) -> int:
        return self.total_capacity - self.currently_used

    def consume(self, amount: int = 1) -> bool:
        if self.available >= amount:
            self.currently_used += amount
            return True
        return False

    def release(self, amount: int = 1):
        self.currently_used = max(0, self.currently_used - amount)

    def to_dict(self) -> dict:
        return {
            "total_capacity": self.total_capacity,
            "currently_used": self.currently_used,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResourceState":
        return cls(
            total_capacity=d.get("total_capacity", 0),
            currently_used=d.get("currently_used", 0),
        )

class ResourceManager:
    def __init__(self):
        self.resources: Dict[str, ResourceState] = {
            "ventilators": ResourceState(total_capacity=5, currently_used=0),
            "icu_beds": ResourceState(total_capacity=10, currently_used=8),
            "blood_units": ResourceState(total_capacity=20, currently_used=5),
            "staff_bandwidth": ResourceState(total_capacity=100, currently_used=40)
        }
        
    def request_intervention_resources(self, procedure_id: str) -> bool:
        """
        Checks if the required resources for a procedure are available and consumes them.
        """
        requirements = {}
        if procedure_id in ("intubation", "ventilator_support"):
            requirements["ventilators"] = 1
            requirements["staff_bandwidth"] = 15
        elif procedure_id == "blood_transfusion":
            requirements["blood_units"] = 2
            requirements["staff_bandwidth"] = 10
        elif procedure_id == "surgical_intervention":
            requirements["icu_beds"] = 1
            requirements["staff_bandwidth"] = 40
            
        # Check availability
        for res, amount in requirements.items():
            if self.resources[res].available < amount:
                return False
                
        # Consume
        for res, amount in requirements.items():
            self.resources[res].consume(amount)

        return True

    def to_dict(self) -> dict:
        return {
            "resources": {
                k: v.to_dict() for k, v in sorted(self.resources.items())
            }
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResourceManager":
        mgr = cls.__new__(cls)
        mgr.resources = {}
        for k, v in d.get("resources", {}).items():
            mgr.resources[k] = ResourceState.from_dict(v) if isinstance(v, dict) else v
        return mgr
