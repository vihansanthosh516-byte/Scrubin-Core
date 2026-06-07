"""Typed API client library for Scrubin Core.

The client is deterministic and immutable – it does not retain mutable state
outside of a lightweight ``httpx`` client instance.  It can be used both against
a live HTTP server (by specifying ``api_base_url``) and in‑process tests by
passing the FastAPI ``app`` – the latter uses ``httpx.ASGITransport`` to talk
directly to the ASGI application without network sockets.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple, Optional

import httpx

from .config import Config


class ScrubinClient:
    """Simple, typed wrapper around the Scrubin HTTP API.

    Parameters
    ----------
    base_url: str, optional
        Base URL of the API (e.g. ``"http://localhost:8000"``).  If omitted the
        ``Config`` value is used.
    timeout: int, optional
        Request timeout in seconds.
    app: FastAPI app, optional
        If provided, the client will use an ``ASGITransport`` to talk directly
        to the application's ASGI interface – useful for test suites.
    """

    def __init__(self, *, base_url: str | None = None, timeout: int | None = None, app: Any | None = None, client: Any | None = None) -> None:
        # Configuration can be overridden via explicit arguments or environment.
        cfg = Config()
        self.base_url = base_url or cfg.api_base_url
        self.timeout = timeout or cfg.timeout
        if client is not None:
            # Directly supplied client (e.g., FastAPI TestClient) – used in unit tests.
            self._client = client
        elif app is not None:
            # In‑process ASGI transport for testing against the FastAPI app.
            transport = httpx.ASGITransport(app=app)
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout, transport=transport)
        else:
            # Regular HTTP client for external services.
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def _url(self, path: str) -> str:
        return path  # httpx client already has base_url set

    def _request(self, method: str, path: str, *, json_body: Any = None, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
        response = self._client.request(method, self._url(path), json=json_body, headers=headers)
        response.raise_for_status()
        # Ensure deterministic ordering in tests by loading with object_pairs_hook
        return json.loads(response.text)

    # ---------------------------------------------------------------------
    # Health & readiness
    # ---------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def ready(self) -> Dict[str, Any]:
        return self._request("GET", "/ready")

    # ---------------------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------------------
    def create_session(self, seed: int, initial_tick: int = 0, *, token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self._request("POST", "/session/create", json_body={"seed": seed, "initial_tick": initial_tick}, headers=headers)

    def get_state(self, session_id: str, *, token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self._request("GET", f"/session/{session_id}/state", headers=headers)

    def post_action(
        self,
        session_id: str,
        action_type: str,
        parameters: Dict[str, Any] | None = None,
        timestamp: int = 0,
        *,
        token: str | None = None,
    ) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self._request(
            "POST",
            f"/session/{session_id}/action",
            json_body={"action_type": action_type, "parameters": parameters or {}, "timestamp": timestamp},
            headers=headers,
        )

    def save_session(self, session_id: str, *, token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self._request("POST", f"/session/{session_id}/save", headers=headers)

    def load_session(self, session_id: str, *, token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self._request("POST", f"/session/{session_id}/load", headers=headers)

    def delete_session(self, session_id: str, *, token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self._request("DELETE", f"/session/{session_id}", headers=headers)

    def list_sessions(self, *, token: str | None = None) -> List[str]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return self._request("GET", "/sessions", headers=headers)
