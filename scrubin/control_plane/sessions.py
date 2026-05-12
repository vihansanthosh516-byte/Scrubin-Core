from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid

@dataclass
class SessionConfig:
    session_id: str = field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:8]}")
    enable_clinical_teams: bool = False
    enable_governance: bool = False
    vectorized: bool = False
    latent_mode: bool = False
    distributed: bool = False
    seed: int = 42
    max_ticks: int = 1440 # 24 hours
    
    overrides: Dict[str, Any] = field(default_factory=dict)

class SessionManager:
    """
    Manages active simulation sessions.
    """
    def __init__(self):
        self.active_sessions: Dict[str, SessionConfig] = {}

    def start_session(self, config: SessionConfig) -> str:
        self.active_sessions[config.session_id] = config
        return config.session_id

    def get_session(self, session_id: str) -> Optional[SessionConfig]:
        return self.active_sessions.get(session_id)

    def terminate_session(self, session_id: str):
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
