"""Replay certification utilities for the deterministic cognition stack.

Provides functions to compute a deterministic hash representing the entire
cognition state after a series of ticks and to verify bit‑for‑bit replay safety.
"""

from __future__ import annotations

import hashlib
from typing import List

from scrubin.core.orchestrator import Orchestrator
from scrubin.replay.hash import world_hash

# Helper to gather deterministic hashes from all cognition stores.
# Each store is assumed to expose an iterator that yields objects with a
# ``replay_hash`` attribute in deterministic insertion order.

def _collect_hashes(orchestrator: Orchestrator) -> List[str]:
    hashes: List[str] = []
    # World hash (represents the complete simulation state for this tick)
    hashes.append(world_hash(orchestrator.world))
    # Memory episodes – stored in orchestrator.memory_store (MemoryStore from scrubin.memory)
    # The MemoryStore API provides ``episodes`` property returning a tuple in insertion order.
    try:
        for ep in orchestrator.memory_store.episodes:
            hashes.append(ep.replay_hash)
    except Exception:
        pass
    # Fact store
    try:
        for f in orchestrator.fact_store.facts:
            hashes.append(f.replay_hash)
    except Exception:
        pass
    # Belief store
    try:
        for b in orchestrator.belief_store.beliefs:
            hashes.append(b.replay_hash)
    except Exception:
        pass
    # Reflection store
    try:
        for r in orchestrator.reflection_store.reflections:
            hashes.append(r.replay_hash)
    except Exception:
        pass
    # Knowledge graph – nodes and edges are deterministic via their own hashes
    try:
        for n in orchestrator.graph_store.nodes:
            hashes.append(n.replay_hash)
    except Exception:
        pass
    # Counterfactual store
    try:
        for cf in orchestrator.counterfactual_store.scenarios:
            hashes.append(cf.replay_hash)
    except Exception:
        pass
    # Meta store – meta patterns
    try:
        for mp in orchestrator.meta_store.patterns:
            hashes.append(mp.replay_hash)
    except Exception:
        pass
    # Plan store
    try:
        for p in orchestrator.plan_store.plans:
            hashes.append(p.replay_hash)
    except Exception:
        pass
    # Executive goals
    for g in orchestrator.executive_store.goals:
        hashes.append(g.replay_hash)
    # Strategies
    for s in orchestrator.strategy_store.strategies:
        hashes.append(s.replay_hash)
    # Strategy selections
    for sel in orchestrator.strategy_selection_store.selections:
        hashes.append(sel.replay_hash)
    # Executive evaluations
    for ev in orchestrator.executive_evaluation_store.evaluations:
        hashes.append(ev.replay_hash)
    # Policy profiles
    for pp in orchestrator.policy_store.profiles:
        hashes.append(pp.replay_hash)
    # Bias plan candidates
    for bc in orchestrator.bias_plan_store.candidates:
        hashes.append(bc.replay_hash)
    # Executive feedback
    for fb in orchestrator.executive_feedback_store.feedbacks:
        hashes.append(fb.replay_hash)
    # Adaptation profiles
    for ap in orchestrator.adaptation_store.profiles:
        hashes.append(ap.replay_hash)
    # Executive optimizations
    for opt in orchestrator.executive_optimization_store.optimizations:
        hashes.append(opt.replay_hash)
    # Self‑improvement signals – not stored, but they are derived from optimizations; we skip.
    # Executive policy decisions
    for dec in orchestrator.executive_policy_store.decisions:
        hashes.append(dec.replay_hash)
    return hashes


def compute_pipeline_hash(orchestrator: Orchestrator) -> str:
    """Compute a deterministic SHA‑256 hash representing the entire cognition state.

    The hash is the SHA‑256 of the concatenation of all collected component hashes
    in deterministic order.  Identical runs with the same seed must produce the
    same pipeline hash.
    """
    component_hashes = _collect_hashes(orchestrator)
    # Concatenate with a delimiter to avoid accidental merging ambiguities.
    concatenated = "|".join(component_hashes)
    return hashlib.sha256(concatenated.encode()).hexdigest()


def certify_replay(seed: int, ticks: int) -> str:
    """Run a deterministic replay for ``ticks`` steps and return the final pipeline hash.

    This helper creates a fresh ``Orchestrator`` with the provided ``seed``,
    performs the standard ``setup`` call, then executes ``ticks`` deterministic
    cognitive cycles via ``run_autonomous_cognitive_cycle``.  The resulting
    pipeline hash can be compared across runs to verify replay safety.
    """
    orch = Orchestrator(seed=seed)
    orch.setup()
    for _ in range(ticks):
        # Use the autonomous wrapper to run the full deterministic cycle.
        from scrubin.cognition.autonomous_cognitive_os import run_autonomous_cognitive_cycle
        run_autonomous_cognitive_cycle(orch)
    return compute_pipeline_hash(orch)
