from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scrubin.world.model import SimulationWorld


@dataclass
class ObservationVector:
    physiology: List[float] = field(default_factory=list)
    organ_health: List[float] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    resources: List[float] = field(default_factory=list)
    temporal: List[float] = field(default_factory=list)

    def to_list(self) -> List[float]:
        return self.physiology + self.organ_health + self.scores + self.resources + self.temporal

    @property
    def dim(self) -> int:
        return len(self.to_list())

    def to_dict(self) -> dict:
        return {
            "physiology": self.physiology,
            "organ_health": self.organ_health,
            "scores": self.scores,
            "resources": self.resources,
            "temporal": self.temporal,
            "dim": self.dim,
        }


_VITAL_KEYS = [
    "spo2", "heart_rate", "bp_systolic", "bp_diastolic",
    "temperature", "respiratory_rate", "consciousness",
]

_ORGAN_KEYS = ["cardiovascular", "respiratory", "renal", "neurologic", "hematologic"]

_SCORE_KEYS = ["mortality_risk", "instability_index", "sofa_score", "news2_score"]

_RESOURCE_KEYS = ["ventilators", "icu_beds", "blood_units", "staff_bandwidth"]


class DictEncoder:
    def encode(self, world: SimulationWorld) -> dict:
        vitals = world.physiology.vitals
        physiology = {k: vitals.get(k, 0.0) for k in _VITAL_KEYS}
        organ_health = {}
        for name in _ORGAN_KEYS:
            organ = getattr(world.organ_state, name, None)
            organ_health[name] = organ.health if organ else 0.0
        scores = {k: getattr(world, k, 0.0) for k in _SCORE_KEYS}
        resources = {}
        for name in _RESOURCE_KEYS:
            r = world.resource_manager.resources.get(name)
            if r is not None:
                resources[f"{name}_available"] = float(r.available)
                resources[f"{name}_used"] = float(r.currently_used)
                resources[f"{name}_capacity"] = float(r.total_capacity)
            else:
                resources[f"{name}_available"] = 0.0
                resources[f"{name}_used"] = 0.0
                resources[f"{name}_capacity"] = 0.0
        temporal = {
            "tick": float(world.tick),
            "n_hidden_conditions": float(len(world.hidden_state)),
            "n_observable_findings": float(len(world.observable_state)),
        }
        return {
            "physiology": physiology,
            "organ_health": organ_health,
            "scores": scores,
            "resources": resources,
            "temporal": temporal,
        }


class TensorEncoder:
    def encode(self, world: SimulationWorld) -> ObservationVector:
        vitals = world.physiology.vitals
        physiology = [round(vitals.get(k, 0.0), 6) for k in _VITAL_KEYS]
        organ_health = []
        for name in _ORGAN_KEYS:
            organ = getattr(world.organ_state, name, None)
            organ_health.append(round(organ.health, 6) if organ else 0.0)
        scores = [round(float(getattr(world, k, 0.0)), 6) for k in _SCORE_KEYS]
        resources = []
        for name in _RESOURCE_KEYS:
            r = world.resource_manager.resources.get(name)
            if r is not None:
                resources.extend([round(float(r.available), 6), round(float(r.currently_used), 6)])
            else:
                resources.extend([0.0, 0.0])
        temporal = [
            float(world.tick),
            float(len(world.hidden_state)),
            float(len(world.observable_state)),
        ]
        return ObservationVector(
            physiology=physiology,
            organ_health=organ_health,
            scores=scores,
            resources=resources,
            temporal=temporal,
        )

    @property
    def dim(self) -> int:
        return (
            len(_VITAL_KEYS)
            + len(_ORGAN_KEYS)
            + len(_SCORE_KEYS)
            + len(_RESOURCE_KEYS) * 2
            + 3
        )


class SequenceEncoder:
    def encode(self, world: SimulationWorld) -> List[List[float]]:
        per_tick = TensorEncoder().encode(world).to_list()
        return [per_tick]

    @property
    def feature_dim(self) -> int:
        return TensorEncoder().dim


class GraphEncoder:
    def encode(self, world: SimulationWorld) -> dict:
        vitals = world.physiology.vitals
        nodes = []
        edges = []
        node_idx = {}
        for name in _ORGAN_KEYS:
            organ = getattr(world.organ_state, name, None)
            health = organ.health if organ else 0.0
            node_idx[name] = len(nodes)
            nodes.append({"type": "organ", "name": name, "health": health})
        for vital_name in _VITAL_KEYS:
            node_idx[vital_name] = len(nodes)
            nodes.append({"type": "vital", "name": vital_name, "value": vitals.get(vital_name, 0.0)})
        organ_edges = [
            ("cardiovascular", "renal"),
            ("cardiovascular", "respiratory"),
            ("respiratory", "cardiovascular"),
        ]
        for src, dst in organ_edges:
            if src in node_idx and dst in node_idx:
                edges.append({"src": node_idx[src], "dst": node_idx[dst], "type": "cascade"})
        return {"nodes": nodes, "edges": edges, "num_nodes": len(nodes)}
