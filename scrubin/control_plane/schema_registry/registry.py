from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Type

@dataclass(frozen=True)
class EventSchema:
    topic: str
    version: int
    fields: Dict[str, Type]
    retention_policy: str = "30d"
    deterministic: bool = True

class EventSchemaRegistry:
    """
    Central authority for all versioned operational event schemas.
    """
    def __init__(self):
        self._schemas: Dict[str, EventSchema] = {}

    def register(self, schema: EventSchema):
        key = f"{schema.topic}:v{schema.version}"
        self._schemas[key] = schema

    def validate(self, topic: str, version: int, payload: Dict[str, Any]) -> bool:
        schema = self.get(topic, version)
        if not schema:
            return False
        
        # Strict field and type validation
        for field_name, expected_type in schema.fields.items():
            if field_name not in payload:
                return False
            if not isinstance(payload[field_name], expected_type):
                return False
        return True

    def get(self, topic: str, version: int) -> Optional[EventSchema]:
        return self._schemas.get(f"{topic}:v{version}")

    def resolve_latest(self, topic: str) -> Optional[EventSchema]:
        topic_schemas = [s for s in self._schemas.values() if s.topic == topic]
        if not topic_schemas:
            return None
        return max(topic_schemas, key=lambda s: s.version)
