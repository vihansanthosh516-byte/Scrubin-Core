from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Immutable user identity record used for authentication & ownership."""
    user_id: str
    email: Optional[str] = None
    created_at: Optional[int] = None  # Unix timestamp; placeholder for now
    provider: Optional[str] = None  # e.g., "supabase", placeholder
