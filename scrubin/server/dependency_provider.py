from __future__ import annotations

from scrubin.api.session_manager import SessionManager
from scrubin.api.persistent_session_store import PersistentSessionStore

# Singleton instances – deterministic, reused across requests.
_SESSION_MANAGER = SessionManager()
_PERSISTENT_STORE = PersistentSessionStore()

def get_session_manager() -> SessionManager:
    """FastAPI dependency returning the shared SessionManager instance."""
    return _SESSION_MANAGER

def get_persistent_store() -> PersistentSessionStore:
    """FastAPI dependency returning the shared PersistentSessionStore instance."""
    return _PERSISTENT_STORE
