import uuid
import random
import time
from typing import Optional

from scrubin.services.simulation_service import SimulationService

_SESSION_TTL_SECONDS = 30 * 60

class SessionManager:
    def __init__(self):
        self._sessions: dict[str, SimulationService] = {}
        self._last_access: dict[str, float] = {}

    def _evict_expired(self):
        now = time.time()
        expired = [sid for sid, t in self._last_access.items() if now - t > _SESSION_TTL_SECONDS]
        for sid in expired:
            del self._sessions[sid]
            del self._last_access[sid]
            print(f"[API] session expired id={sid}")

    def create(self, seed: int, profile_name: str, patient_profile_id: str = "standard",
               mode: str = "autonomous") -> SimulationService:
        self._evict_expired()
        
        session = SimulationService.create_session(
            seed=seed,
            profile_name=profile_name,
            patient_profile_id=patient_profile_id,
            mode=mode,
        )
        self._sessions[session.session_id] = session
        self._last_access[session.session_id] = time.time()
        print(f"[API] session created id={session.session_id} seed={seed} profile={profile_name} patient={patient_profile_id} mode={mode}")
        return session

    def get(self, session_id: str) -> Optional[SimulationService]:
        self._evict_expired()
        session = self._sessions.get(session_id)
        if session:
            self._last_access[session_id] = time.time()
        return session

    def reset(self, session_id: str) -> Optional[SimulationService]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        new_session = session.reset_session()
        self._sessions[session_id] = new_session
        self._last_access[session_id] = time.time()
        print(f"[API] session reset id={session_id}")
        return new_session
