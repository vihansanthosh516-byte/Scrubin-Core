"""Configuration module for Scrubin Frontend Integration.

Provides a simple immutable dataclass that reads environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable configuration loaded from environment variables.

    Attributes
    ----------
    api_base_url: str
        Base URL for the Scrubin HTTP API (e.g. ``http://localhost:8000``).
    timeout: int
        Request timeout in seconds.
    """

    api_base_url: str = field(default_factory=lambda: os.getenv("SCRUBIN_API_URL", "http://localhost"))
    timeout: int = field(default_factory=lambda: int(os.getenv("SCRUBIN_TIMEOUT", "30")))
