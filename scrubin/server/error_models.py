from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class APIError(Exception):
    """Base immutable error model for HTTP API responses."""
    message: str
    code: Optional[int] = None

@dataclass(frozen=True, slots=True)
class ValidationError(APIError):
    """Invalid request payload or parameters."""
    pass


@dataclass(frozen=True, slots=True)
class SessionNotFoundError(APIError):
    """Requested session identifier does not exist."""
    pass


@dataclass(frozen=True, slots=True)
class SerializationError(APIError):
    """Error during (de)serialization of WorldState or metadata."""
    pass


@dataclass(frozen=True, slots=True)
class PersistenceError(APIError):
    """Error interacting with the persistence layer (e.g., I/O)."""
    pass
