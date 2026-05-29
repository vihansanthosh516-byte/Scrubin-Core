# Engine package for procedural cognition primitives

__all__ = [
    "procedure",
    "decision_node",
    "complication_engine",
    "physiology_engine",
    "option_generator",
]

# Import side‑effects – loading the Phase A node definitions registers them.
# The import is deliberately placed after ``__all__`` so that tools such as
# ``pydoc`` still see a clean public interface.
from . import decision_nodes_phase_a  # noqa: F401

# Validate the registry at import time – this will raise if structural problems
# are detected, making failures immediate and easy to debug.
from .decision_registry import DecisionRegistry

DecisionRegistry.validate()

