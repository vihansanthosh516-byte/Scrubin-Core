"""Deterministic immutable models for Phase 8.0 learning subsystem.
All dataclasses are frozen, use ``slots=True``, store immutable tuples only,
and expose a ``deterministic_hash`` property based on a stable SHA‑256 hash
over a JSON‑encoded representation of their primitive fields.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Tuple, Any


def _det_hash(obj: Any) -> int:
    """Return a deterministic integer hash for a dataclass instance.

    Attempts to serialise the object to a JSON‑compatible dict using ``asdict``.
    ``asdict`` may raise if a field (e.g. a post‑init ``deterministic_hash``
    attribute) is not yet set. In that case we fall back to constructing a dict
    of the existing fields via ``dataclasses.fields`` and ``getattr`` – this
    avoids invoking ``__repr__``/``__str__`` which can trigger the same error.
    If that also fails we finally fall back to ``repr(obj)``.
    """
    try:
        data = asdict(obj)  # type: ignore[arg-type]
    except Exception:
        try:
            from dataclasses import fields
            data = {f.name: getattr(obj, f.name) for f in fields(obj) if hasattr(obj, f.name)}
        except Exception:
            data = repr(obj)
    try:
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    except Exception:
        # Fallback to string representation for non‑serializable values (e.g., opaque objects).
        json_str = json.dumps(str(data), sort_keys=True, separators=(",", ":"))
    # Truncate to 64‑bit signed int for consistency with other hash uses.
    digest = hashlib.sha256(json_str.encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


# ---------------------------------------------------------------------------
# Core learning entity models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ExperiencePattern:
    """Deterministic description of a discovered experience pattern.

    ``pattern_id`` – unique identifier (lexical).
    ``description`` – human readable text.
    ``confidence`` – float in [0, 1].
    """

    pattern_id: str
    description: str
    confidence: float = 0.0

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class LearnedPolicy:
    """Immutable representation of a learned policy.

    ``policy_id`` – deterministic identifier.
    ``version`` – integer version.
    ``confidence`` – float in [0, 1].
    """

    policy_id: str
    version: int
    confidence: float = 0.0

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class SurgicalLesson:
    """A deterministic lesson derived from observations.

    ``lesson_id`` – unique identifier.
    ``content`` – description.
    ``usefulness`` – float rating.
    """

    lesson_id: str
    content: str
    usefulness: float = 0.0

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class ConfidenceUpdate:
    """Record of a confidence adjustment for a policy or lesson.

    ``target_id`` – identifier of the policy/lesson being updated.
    ``delta`` – signed change applied.
    """

    target_id: str
    delta: float

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class GeneralizedRule:
    """Deterministic rule derived from multiple experiences.

    ``rule_id`` – unique identifier.
    ``description`` – textual description.
    """

    rule_id: str
    description: str

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


# ---------------------------------------------------------------------------
# Top‑level immutable learning snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LearningSnapshot:
    """Immutable aggregation of all learning artefacts for a tick.

    Collections are stored as sorted ``tuple`` objects to guarantee deterministic
    ordering regardless of insertion order.
    """

    tick: int = 0
    experience_patterns: Tuple[ExperiencePattern, ...] = field(default_factory=tuple)
    learned_policies: Tuple[LearnedPolicy, ...] = field(default_factory=tuple)
    surgical_lessons: Tuple[SurgicalLesson, ...] = field(default_factory=tuple)
    confidence_updates: Tuple[ConfidenceUpdate, ...] = field(default_factory=tuple)
    generalized_rules: Tuple[GeneralizedRule, ...] = field(default_factory=tuple)
    deterministic_hash: int = field(init=False)

    def __post_init__(self):
        # Ensure deterministic ordering for each collection based on the primary identifier.
        object.__setattr__(self, "experience_patterns", tuple(sorted(self.experience_patterns, key=lambda x: x.pattern_id)))
        object.__setattr__(self, "learned_policies", tuple(sorted(self.learned_policies, key=lambda x: (x.policy_id, x.version))))
        object.__setattr__(self, "surgical_lessons", tuple(sorted(self.surgical_lessons, key=lambda x: x.lesson_id)))
        object.__setattr__(self, "confidence_updates", tuple(sorted(self.confidence_updates, key=lambda x: x.target_id)))
        object.__setattr__(self, "generalized_rules", tuple(sorted(self.generalized_rules, key=lambda x: x.rule_id)))
        # Compute deterministic hash over the fully ordered content.
        # Set a temporary placeholder to allow asdict to succeed.
        object.__setattr__(self, "deterministic_hash", 0)
        object.__setattr__(self, "deterministic_hash", _det_hash(self))
