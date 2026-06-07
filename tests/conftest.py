import pytest
from scrubin.server import dependency_provider as dp
from scrubin.api.session_manager import SessionManager
from scrubin.api.persistent_session_store import PersistentSessionStore

@pytest.fixture(autouse=True)
def isolated_http_backend(tmp_path, monkeypatch):
    """Provide isolated SessionManager and PersistentSessionStore for each test.

    - `tmp_path` gives a fresh temporary directory for persistence.
    - `SessionManager` is instantiated anew, ensuring no in‑memory sessions leak.
    - Dependency injection functions are monkey‑patched to return these fresh instances.
    """
    manager = SessionManager()
    store = PersistentSessionStore(storage_dir=str(tmp_path))
    monkeypatch.setattr(dp, "get_session_manager", lambda: manager)
    monkeypatch.setattr(dp, "get_persistent_store", lambda: store)
    # No explicit yield needed; fixtures clean up automatically.
    return
