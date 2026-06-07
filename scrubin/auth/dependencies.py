from fastapi import Request
from .user import UserIdentity

def get_current_user(request: Request) -> UserIdentity:
    """Placeholder authentication dependency.

    In a real deployment this would verify a Supabase JWT. For now we simply
    read the ``Authorization`` header. If the header is of the form ``Bearer <user_id>``
    we treat ``<user_id>`` as the authenticated user identifier. Otherwise a default
    user ``default_user`` is used – sufficient for tests that do not exercise auth.
    """
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        # In a real scenario the token would be decoded to extract user info.
        return UserIdentity(user_id=token)
    # Fallback default user (used by existing tests).
    return UserIdentity(user_id="default_user")