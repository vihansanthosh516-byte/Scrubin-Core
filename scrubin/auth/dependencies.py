from __future__ import annotations

import os
from fastapi import HTTPException, Request, status
from .user import UserIdentity

# Auth mode controls how strict authentication is.
#   "dev"     – trust a Bearer <user_id> header as a stand-in identity (default;
#               suitable for local tests where real JWT verification is not wired up).
#   "jwt"     – require a real JWT and a configured verification path (e.g. Supabase).
#               When this mode is enabled without a JWT verifier configured, requests
#               fail closed with 401 rather than silently trusting the header.
_AUTH_MODE = os.getenv("SCRUBIN_AUTH_MODE", "dev").strip().lower()


def _authenticate_dev(request: Request) -> UserIdentity:
    """Dev-mode auth: treat ``Bearer <user_id>`` as the identity, else default user.

    This intentionally mirrors the original placeholder behaviour so existing tests
    that send no Authorization header continue to receive ``default_user``.
    """
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token:
            return UserIdentity(user_id=token, provider="dev-bearer")
    return UserIdentity(user_id="default_user", provider="dev-default")


def _authenticate_jwt(request: Request) -> UserIdentity:
    """Production-mode auth: verify a real JWT.

    A full JWT verifier (e.g. Supabase JWKS + signature/exp/iss/aud checks) must be
    plugged in here. Until one is configured, requests fail closed.
    """
    jwks_url = os.getenv("SCRUBIN_JWKS_URL", "").strip()
    if not jwks_url:
        # Fail closed: do not silently trust bearer strings in production mode.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SCRUBIN_AUTH_MODE=jwt requires SCRUBIN_JWKS_URL to be configured",
        )
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # NOTE: Plug in real JWT verification here (PyJWKClient + decode). Identity fields
    # (user_id, email) should be extracted from the validated claims.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="JWT verification is configured but no verifier implementation is installed",
    )


def get_current_user(request: Request) -> UserIdentity:
    """Resolve the authenticated user for the current request.

    Behaviour is governed by ``SCRUBIN_AUTH_MODE``:

    * ``dev`` (default) – dev/test stand-in that reads ``Bearer <user_id>`` or
      falls back to ``default_user``. NEVER use this mode in production.
    * ``jwt`` – fail‑closed production mode requiring a real JWT verifier.
    """
    if _AUTH_MODE == "jwt":
        return _authenticate_jwt(request)
    return _authenticate_dev(request)