import uuid
import random
import time
import logging
from typing import Optional

from scrubin.services.simulation_service import SimulationService

_SESSION_TTL_SECONDS = 30 * 60

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self._sessions: dict[str, SimulationService] = {}
        self._last_access: dict[str, float] = {}
        # owner_user_id per session; consulted by protected routes via getattr.
        self._owners: dict[str, str] = {}

    def _evict_expired(self):
        now = time.time()
        expired = [sid for sid, t in self._last_access.items() if now - t > _SESSION_TTL_SECONDS]
        for sid in expired:
            del self._sessions[sid]
            del self._last_access[sid]
            self._owners.pop(sid, None)
            logger.info("session expired id=%s", sid)

    def create(self, seed: int, profile_name: str, patient_profile_id: str = "standard",
               mode: str = "autonomous", procedure_id: str | None = None, variant_id: str | None = None,
               owner_user_id: str = "default_user") -> SimulationService:
        self._evict_expired()
        
        session = SimulationService.create_session(
            seed=seed,
            profile_name=profile_name,
            patient_profile_id=patient_profile_id,
            mode=mode,
            procedure_id=procedure_id,
            variant_id=variant_id,
        )
        self._sessions[session.session_id] = session
        self._last_access[session.session_id] = time.time()
        self._owners[session.session_id] = owner_user_id
        logger.info("session created id=%s seed=%s profile=%s patient=%s mode=%s owner=%s",
                    session.session_id, seed, profile_name, patient_profile_id, mode, owner_user_id)
        return session

    def get(self, session_id: str) -> Optional[SimulationService]:
        self._evict_expired()
        session = self._sessions.get(session_id)
        if session:
            self._last_access[session_id] = time.time()
        return session

    def owner_of(self, session_id: str) -> Optional[str]:
        """Return the owning user_id for a session, or None if unknown."""
        return self._owners.get(session_id)

    def reset(self, session_id: str) -> Optional[SimulationService]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        new_session = session.reset_session()
        self._sessions[session_id] = new_session
        self._last_access[session_id] = time.time()
        logger.info("session reset id=%s", session_id)
        return new_session
