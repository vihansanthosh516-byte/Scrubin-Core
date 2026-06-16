"""Deterministic multi‑system physiology package.

Provides immutable dataclasses for individual organ systems and a set of
pure, deterministic engines that model inter‑system interactions, homeostatic
compensation, feedback loops, perfusion calculations, and metabolism.

All engines accept an immutable ``SystemsState`` snapshot and return a new
snapshot via ``dataclasses.replace`` – no side‑effects, no randomness, no
external APIs.
"""

from .models import (
    CardiovascularSystem,
    RespiratorySystem,
    RenalSystem,
    HepaticSystem,
    NeurologicSystem,
    EndocrineSystem,
    ImmuneSystem,
    MetabolicSystem,
    SystemsState,
)
from .interaction_engine import InteractionEngine
from .homeostasis_engine import HomeostasisEngine
from .feedback_engine import FeedbackEngine
from .perfusion_engine import PerfusionEngine
from .metabolism_engine import MetabolismEngine

__all__ = [
    "CardiovascularSystem",
    "RespiratorySystem",
    "RenalSystem",
    "HepaticSystem",
    "NeurologicSystem",
    "EndocrineSystem",
    "ImmuneSystem",
    "MetabolicSystem",
    "SystemsState",
    "InteractionEngine",
    "HomeostasisEngine",
    "FeedbackEngine",
    "PerfusionEngine",
    "MetabolismEngine",
]
