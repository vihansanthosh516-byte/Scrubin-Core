"""Scenario package – deterministic, immutable procedure definitions.

Provides the :class:`ScenarioRegistry` for loading, validating, and hashing
scenario definitions.  All scenarios are pure data – the simulation engine
consumes them without any procedural branching logic.
"""

from .registry import ScenarioRegistry
