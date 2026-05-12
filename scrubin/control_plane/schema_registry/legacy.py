from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import json

@dataclass
class SchemaDefinition:
    name: str
    version: str
    schema: Dict[str, Any]
    description: str

class SchemaRegistry:
    """
    Central registry for ALL Control Plane schemas.
    """
    def __init__(self):
        self._schemas: Dict[str, SchemaDefinition] = {}
        self._load_default_schemas()

    def _load_default_schemas(self):
        # ExperimentSchema
        self.register("ExperimentSchema", "1.0", {
            "experiment_id": "string",
            "phase": "int",
            "mode": ["SIMULATION", "TRAINING", "DISTRIBUTED"],
            "config": {
                "mcts_iterations": "int",
                "max_depth": "int",
                "deterministic": "bool"
            },
            "flags": {
                "governance_enabled": "bool",
                "latent_world_model": "bool"
            }
        }, "Configuration for clinical experiments.")

        # JobSchema
        self.register("JobSchema", "1.0", {
            "job_id": "string",
            "job_type": ["HIERARCHICAL_SIM", "VECTOR_BATCH", "MULTI_AGENT"],
            "priority": "int",
            "payload": "object",
            "created_at_tick": "int"
        }, "Definition for scheduled orchestration jobs.")

        # SnapshotSchema
        self.register("SnapshotSchema", "1.0", {
            "snapshot_id": "string",
            "world_hash": "string",
            "tick": "int",
            "state_blob": "object",
            "deterministic_seed": "int"
        }, "Schema for deterministic state snapshots.")

    def register(self, name: str, version: str, schema: Dict[str, Any], description: str):
        self._schemas[f"{name}:{version}"] = SchemaDefinition(name, version, schema, description)

    def get(self, name: str, version: str = "1.0") -> Optional[SchemaDefinition]:
        return self._schemas.get(f"{name}:{version}")

    def validate(self, name: str, payload: Dict[str, Any]) -> bool:
        """
        Stub for actual validation logic (e.g., using jsonschema).
        For now, performs basic key and type checking.
        """
        definition = self.get(name)
        if not definition:
            return False
        
        # Simple recursive check (Simplified for implementation)
        return self._recursive_validate(definition.schema, payload)

    def _recursive_validate(self, schema: Any, data: Any) -> bool:
        if isinstance(schema, str):
            if schema == "string": return isinstance(data, str)
            if schema == "int": return isinstance(data, int)
            if schema == "bool": return isinstance(data, bool)
            if schema == "object": return isinstance(data, dict)
            return True
        if isinstance(schema, list):
            return data in schema
        if isinstance(schema, dict):
            if not isinstance(data, dict): return False
            for k, v in schema.items():
                if k in data:
                    if not self._recursive_validate(v, data[k]):
                        return False
            return True
        return True
