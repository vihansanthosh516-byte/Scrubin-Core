"""Tests for deterministic Phase 8.0 learning snapshot.
The suite checks that the ``LearningSnapshot`` is immutable, deterministic, and
uses ``replace``‑style updates (via the ``LearningManager``).
"""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from scrubin.learning.models import (
    ExperiencePattern,
    LearnedPolicy,
    SurgicalLesson,
    ConfidenceUpdate,
    GeneralizedRule,
    LearningSnapshot,
)
from scrubin.learning.learning_manager import LearningManager


def build_sample_data():
    # Provide unsorted collections to test deterministic ordering.
    eps = (
        ExperiencePattern(pattern_id="p2", description="second", confidence=0.2),
        ExperiencePattern(pattern_id="p1", description="first", confidence=0.9),
    )
    policies = (
        LearnedPolicy(policy_id="polB", version=1, confidence=0.5),
        LearnedPolicy(policy_id="polA", version=2, confidence=0.8),
    )
    lessons = (
        SurgicalLesson(lesson_id="l2", content="lesson B", usefulness=0.3),
        SurgicalLesson(lesson_id="l1", content="lesson A", usefulness=0.7),
    )
    confs = (
        ConfidenceUpdate(target_id="polA", delta=0.1),
        ConfidenceUpdate(target_id="polB", delta=-0.2),
    )
    rules = (
        GeneralizedRule(rule_id="r2", description="rule two"),
        GeneralizedRule(rule_id="r1", description="rule one"),
    )
    return eps, policies, lessons, confs, rules


def test_snapshot_immutability_and_ordering():
    eps, policies, lessons, confs, rules = build_sample_data()
    snap = LearningManager.snapshot(
        tick=5,
        experience_patterns=eps,
        learned_policies=policies,
        surgical_lessons=lessons,
        confidence_updates=confs,
        generalized_rules=rules,
    )
    # Verify deterministic ordering (by ID fields).
    assert tuple(p.pattern_id for p in snap.experience_patterns) == ("p1", "p2")
    assert tuple(p.policy_id for p in snap.learned_policies) == ("polA", "polB")
    assert tuple(l.lesson_id for l in snap.surgical_lessons) == ("l1", "l2")
    assert tuple(c.target_id for c in snap.confidence_updates) == ("polA", "polB")
    assert tuple(r.rule_id for r in snap.generalized_rules) == ("r1", "r2")
    # Snapshot should be frozen.
    with pytest.raises(FrozenInstanceError):
        snap.tick = 10


def test_deterministic_hash_stability():
    eps, policies, lessons, confs, rules = build_sample_data()
    snap1 = LearningManager.snapshot(
        tick=7,
        experience_patterns=eps,
        learned_policies=policies,
        surgical_lessons=lessons,
        confidence_updates=confs,
        generalized_rules=rules,
    )
    snap2 = LearningManager.snapshot(
        tick=7,
        experience_patterns=eps,
        learned_policies=policies,
        surgical_lessons=lessons,
        confidence_updates=confs,
        generalized_rules=rules,
    )
    assert snap1.deterministic_hash == snap2.deterministic_hash


from dataclasses import replace

def test_replace_based_update():
    # Build an initial snapshot, then produce a new one using ``replace``.
    eps, policies, lessons, confs, rules = build_sample_data()
    base = LearningManager.snapshot(tick=3, experience_patterns=eps)
    # Use ``replace`` to change tick without mutating ``base``.
    new = replace(base, tick=4)
    assert base.tick == 3
    assert new.tick == 4
    # Hashes must differ because tick is part of the hash.
    assert base.deterministic_hash != new.deterministic_hash
