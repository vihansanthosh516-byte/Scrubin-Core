import pytest
import warnings
import pytest
# Suppress pytest warnings about directly calling fixture functions – tests intentionally do this.
warnings.filterwarnings("ignore", "Fixture .* called directly", category=pytest.PytestWarning)

def pytest_collection_modifyitems(config, items):
    """Patch fixture wrappers that are called directly in tests.

    The `bleed_comp` fixture in ``test_intervention_engine.py`` is called directly
    which triggers a ``fixture called directly`` failure in recent pytest versions.
    We replace the wrapper with the original function (available as ``__wrapped__``)
    to allow direct calls while preserving fixture registration for any pytest
    injection usage.
    """
    for item in items:
        mod = getattr(item, "module", None)
        if mod is None:
            continue
        # Target only the specific test module that calls the fixture directly.
        if mod.__name__.endswith("test_intervention_engine"):
            for func_name in ["bleed_comp"]:
                func = getattr(mod, func_name, None)
                if func and hasattr(func, "__wrapped__"):
                    setattr(mod, func_name, func.__wrapped__)

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
