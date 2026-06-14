"""Deterministic statistics summarizing the entire cognition pipeline.

All functions compute aggregates directly from the orchestrator's stores – no
caches, no mutable state.  The results are deterministic because the underlying
stores preserve insertion order and provide immutable objects.
"""

from __future__ import annotations

from typing import Dict

from scrubin.core.orchestrator import Orchestrator


def episode_count(orch: Orchestrator) -> int:
    try:
        return len(orch.memory_store.episodes)
    except Exception:
        return 0


def fact_count(orch: Orchestrator) -> int:
    try:
        return len(orch.fact_store.facts)
    except Exception:
        return 0


def belief_count(orch: Orchestrator) -> int:
    try:
        return len(orch.belief_store.beliefs)
    except Exception:
        return 0


def reflection_count(orch: Orchestrator) -> int:
    try:
        return len(orch.reflection_store.reflections)
    except Exception:
        return 0


def graph_node_count(orch: Orchestrator) -> int:
    try:
        return len(orch.graph_store.nodes)
    except Exception:
        return 0


def counterfactual_count(orch: Orchestrator) -> int:
    try:
        return len(orch.counterfactual_store.scenarios)
    except Exception:
        return 0


def meta_pattern_count(orch: Orchestrator) -> int:
    try:
        return len(orch.meta_store.patterns)
    except Exception:
        return 0


def plan_count(orch: Orchestrator) -> int:
    try:
        return len(orch.plan_store.plans)
    except Exception:
        return 0


def goal_count(orch: Orchestrator) -> int:
    return len(orch.executive_store.goals)


def strategy_count(orch: Orchestrator) -> int:
    return len(orch.strategy_store.strategies)


def selection_count(orch: Orchestrator) -> int:
    return len(orch.strategy_selection_store.selections)


def evaluation_count(orch: Orchestrator) -> int:
    return len(orch.executive_evaluation_store.evaluations)


def policy_profile_count(orch: Orchestrator) -> int:
    return len(orch.policy_store.profiles)


def bias_plan_candidate_count(orch: Orchestrator) -> int:
    return len(orch.bias_plan_store.candidates)


def feedback_count(orch: Orchestrator) -> int:
    return len(orch.executive_feedback_store.feedbacks)


def adaptation_profile_count(orch: Orchestrator) -> int:
    return len(orch.adaptation_store.profiles)


def optimization_count(orch: Orchestrator) -> int:
    return len(orch.executive_optimization_store.optimizations)


def policy_decision_count(orch: Orchestrator) -> int:
    return len(orch.executive_policy_store.decisions)


def pipeline_summary(orch: Orchestrator) -> Dict[str, int]:
    """Return a dictionary of key pipeline counts for quick inspection."""
    return {
        "episodes": episode_count(orch),
        "facts": fact_count(orch),
        "beliefs": belief_count(orch),
        "reflections": reflection_count(orch),
        "graph_nodes": graph_node_count(orch),
        "counterfactuals": counterfactual_count(orch),
        "meta_patterns": meta_pattern_count(orch),
        "plans": plan_count(orch),
        "goals": goal_count(orch),
        "strategies": strategy_count(orch),
        "selections": selection_count(orch),
        "evaluations": evaluation_count(orch),
        "policy_profiles": policy_profile_count(orch),
        "bias_candidates": bias_plan_candidate_count(orch),
        "feedbacks": feedback_count(orch),
        "adaptations": adaptation_profile_count(orch),
        "optimizations": optimization_count(orch),
        "policy_decisions": policy_decision_count(orch),
    }
