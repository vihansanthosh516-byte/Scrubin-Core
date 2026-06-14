"""Deterministic executive policy arbitration engine.

Combines adaptation, policy, optimization, and self‑improvement signals to
produce a final immutable ``ExecutivePolicyDecision`` for each executive goal.
All operations are pure cognition – no world mutation.
"""

from __future__ import annotations

from typing import List, Tuple, Dict

from .executive_policy_decision import ExecutivePolicyDecision
from .executive_policy_store import ExecutivePolicyStore
from .executive_optimization import ExecutiveOptimization
from .policy_profile import PolicyProfile
from .adaptation_profile import AdaptationProfile
from .executive_self_improvement import ExecutiveImprovementSignal
from .strategy_selection import StrategySelection
from .strategy_selection_store import StrategySelectionStore
from .strategy_store import StrategyStore
from .executive_store import ExecutiveStore


def _component_score(opt_score: float, policy_conf: float, adapt_conf: float, imp_conf: float) -> float:
    """Weighted arbitration score as specified.
    """
    return 0.40 * opt_score + 0.25 * policy_conf + 0.20 * adapt_conf + 0.15 * imp_conf


def update_executive_policy(
    executive_store: ExecutiveStore,
    selection_store: StrategySelectionStore,
    policy_store: "scrubin.cognition.policy_store.PolicyStore",
    adaptation_store: "scrubin.cognition.adaptation_store.AdaptationStore",
    optimization_store: "scrubin.cognition.executive_optimization_store.ExecutiveOptimizationStore",
    strategy_store: "scrubin.cognition.strategy_store.StrategyStore",
    self_improvement_signals: List[ExecutiveImprovementSignal],
    policy_store_obj: ExecutivePolicyStore,
) -> None:
    """Create or update ``ExecutivePolicyDecision`` objects for each goal.

    For each executive goal we evaluate every available strategy, compute a
    deterministic arbitration score, select the best strategy, and store a
    ``ExecutivePolicyDecision`` with supporting IDs. Deterministic merge
    semantics are handled by ``ExecutivePolicyStore.add_or_update``.
    """
    # Build quick lookup maps
    # Strategy selections (by (goal_id, strategy_id) -> selection id)
    sel_map: Dict[Tuple[str, str], StrategySelection] = {}
    for sel in selection_store.selections:
        sel_map[(sel.goal_id, sel.strategy_id)] = sel

    # Policy confidences and profile IDs
    policy_conf_map: Dict[str, float] = {}
    policy_id_map: Dict[str, str] = {}
    for prof in policy_store.profiles:
        policy_conf_map[prof.strategy_id] = prof.confidence
        policy_id_map[prof.strategy_id] = prof.id

    # Adaptation confidences and profile IDs
    adapt_conf_map: Dict[str, float] = {}
    adapt_id_map: Dict[str, str] = {}
    for ap in adaptation_store.profiles:
        adapt_conf_map[ap.strategy_id] = ap.confidence
        adapt_id_map[ap.strategy_id] = ap.id

    # Optimization scores, confidences and IDs
    opt_score_map: Dict[str, float] = {}
    opt_conf_map: Dict[str, float] = {}
    opt_id_map: Dict[str, str] = {}
    for opt in optimization_store.optimizations:
        opt_score_map[opt.strategy_id] = opt.optimization_score
        opt_conf_map[opt.strategy_id] = opt.confidence
        opt_id_map[opt.strategy_id] = opt.id

    # Self‑improvement signals confidence and IDs
    imp_conf_map: Dict[str, float] = {}
    imp_id_map: Dict[str, str] = {}
    for sig in self_improvement_signals:
        imp_conf_map[sig.strategy_id] = sig.confidence
        imp_id_map[sig.strategy_id] = sig.id

    # All strategies known
    all_strategy_ids = [s.id for s in strategy_store.strategies]

    # Process each goal
    for goal in executive_store.goals:
        # Compute scores for each candidate strategy
        scores: List[Tuple[str, float, float]] = []  # (strategy_id, score, confidence)
        for sid in all_strategy_ids:
            opt_score = opt_score_map.get(sid, 0.0)
            policy_conf = policy_conf_map.get(sid, 0.0)
            adapt_conf = adapt_conf_map.get(sid, 0.0)
            imp_conf = imp_conf_map.get(sid, 0.0)
            arb_score = _component_score(opt_score, policy_conf, adapt_conf, imp_conf)
            # Overall confidence weighted similarly (using same component confidences)
            overall_conf = (0.40 * opt_conf_map.get(sid, 0.0) +
                            0.25 * policy_conf +
                            0.20 * adapt_conf +
                            0.15 * imp_conf)
            scores.append((sid, arb_score, overall_conf))
        # Determine best strategy using deterministic tie‑breakers
        # Sort by (-score, -confidence, -support_count, strategy_id)
        # Support count = number of supporting IDs (policy+adapt+opt+signal)
        def support_count(sid: str) -> int:
            cnt = 0
            cnt += 1 if sid in policy_conf_map else 0
            cnt += 1 if sid in adapt_conf_map else 0
            cnt += 1 if sid in opt_score_map else 0
            cnt += 1 if sid in imp_conf_map else 0
            return cnt
        best = sorted(
            scores,
            key=lambda entry: (
                -entry[1],                     # higher arbitration score
                -entry[2],                     # higher confidence
                -support_count(entry[0]),      # more supporting evidence
                entry[0],                      # lexicographically smaller ID
            ),
        )[0]
        selected_sid, selected_score, selected_conf = best
        # Determine rejected ids (all others)
        rejected = tuple(sorted(sid for sid in all_strategy_ids if sid != selected_sid))
        # Gather supporting IDs
        # Selection ID for selected strategy (if exists)
        sel = sel_map.get((goal.id, selected_sid))
        sel_id = (sel.id,) if sel else ()
        policy_pid = (policy_id_map[selected_sid],) if selected_sid in policy_id_map else ()
        adapt_pid = (adapt_id_map[selected_sid],) if selected_sid in adapt_id_map else ()
        opt_pid = (opt_id_map[selected_sid],) if selected_sid in opt_id_map else ()
        imp_pid = (imp_id_map[selected_sid],) if selected_sid in imp_id_map else ()
        decision = ExecutivePolicyDecision.create(
            goal_id=goal.id,
            selected_strategy_id=selected_sid,
            arbitration_score=selected_score,
            confidence=selected_conf,
            rejected_strategy_ids=rejected,
            supporting_strategy_selection_ids=sel_id,
            supporting_policy_profile_ids=policy_pid,
            supporting_adaptation_profile_ids=adapt_pid,
            supporting_optimization_ids=opt_pid,
            supporting_signal_ids=imp_pid,
            first_seen_tick=goal.created_tick,
            last_seen_tick=goal.created_tick,
        )
        policy_store_obj.add_or_update(decision)
