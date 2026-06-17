"""LearningManager – builds a deterministic ``LearningSnapshot``.
All updates are performed using ``dataclasses.replace`` to preserve immutability.
The manager currently aggregates data from the Cognitive ``LearningState`` and
placeholder collections defined in ``scrubin.learning.models``.  No mutable
global state is used; the function returns a brand‑new snapshot each call.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Tuple

from scrubin.cognition.learning_state import LearningState
from .models import (
    LearningSnapshot,
    ExperiencePattern,
    LearnedPolicy,
    SurgicalLesson,
    ConfidenceUpdate,
    GeneralizedRule,
)


class LearningManager:
    """Factory for deterministic ``LearningSnapshot`` objects.

    The manager is deliberately lightweight – it extracts lightweight
    deterministic artefacts from the provided ``LearningState`` (if any) and
    combines them with optional auxiliary collections.
    """

    @staticmethod
    def snapshot(
        *,
        tick: int = 0,
        learning_state: LearningState | None = None,
        experience_patterns: Tuple[ExperiencePattern, ...] = (),
        learned_policies: Tuple[LearnedPolicy, ...] = (),
        surgical_lessons: Tuple[SurgicalLesson, ...] = (),
        confidence_updates: Tuple[ConfidenceUpdate, ...] = (),
        generalized_rules: Tuple[GeneralizedRule, ...] = (),
    ) -> LearningSnapshot:
        """Create an immutable ``LearningSnapshot``.

        * ``learning_state`` – optional ``LearningState`` from the cognition
          subsystem.  Its ``patterns`` and ``beliefs`` are converted into
          ``ExperiencePattern`` and ``SurgicalLesson`` objects respectively.
        * All collections are stored as immutable tuples and sorted inside the
          ``LearningSnapshot`` dataclass.
        """
        # Use provided collections directly; optionally extend with LearningState data.
        ep: Tuple[ExperiencePattern, ...] = experience_patterns
        sl: Tuple[SurgicalLesson, ...] = surgical_lessons
        if learning_state is not None:
            # Append patterns from learning_state to the provided collections.
            ep = tuple(
                ExperiencePattern(
                    pattern_id=p.pattern_id,
                    description=p.description,
                    confidence=p.confidence,
                )
                for p in learning_state.patterns
            ) + ep
            sl = tuple(
                SurgicalLesson(
                    lesson_id=b.belief_id,
                    content=b.description,
                    usefulness=b.confidence,
                )
                for b in learning_state.beliefs
            ) + sl
        # Build snapshot – the dataclass will sort internally.
        return LearningSnapshot(
            tick=tick,
            experience_patterns=ep,
            learned_policies=learned_policies,
            surgical_lessons=sl,
            confidence_updates=confidence_updates,
            generalized_rules=generalized_rules,
        )
