"""Deterministic adaptive engine unit tests.

These tests verify that the Phase 8.1 deterministic adaptive planning pipeline
produces repeatable results – identical inputs must yield identical immutable
snapshots, policy ordering, action ordering, contingency generation, and
simulation preview hashes.
"""

from scrubin.adaptive import AdaptiveManager


def test_deterministic_adaptive_pipeline():
    manager = AdaptiveManager()

    # Minimal deterministic context – all objects are simple dicts/lists.
    context = {
        "learned_policies": [
            {"policy_id": "p_low", "priority": 1, "confidence": 0.5},
            {"policy_id": "p_high", "priority": 2, "confidence": 0.4},
        ],
        "executive_goals": [
            {"policy_id": "goal1", "priority": 3, "confidence": 0.9},
        ],
        # No additional sources – defaults to empty.
        "action_metrics": {
            "obtain_exposure": {"mortality_risk": 0.1, "physiology_instability": 0.2},
            "clip_vessel": {"mortality_risk": 0.3, "physiology_instability": 0.1},
        },
    }

    snapshot1 = manager.generate_snapshot(context)
    snapshot2 = manager.generate_snapshot(context)

    # 1. Overall deterministic hash must be identical.
    assert snapshot1.deterministic_hash == snapshot2.deterministic_hash

    # 2. Policy selection ordering – priority desc, confidence desc, id.
    selected_ids = [c.policy_id for c in snapshot1.selected_policy_candidates]
    assert selected_ids == ["goal1", "p_high", "p_low"]

    # 3. Adaptive plan actions – static canonical sequence.
    action_ids = [a.action_id for a in snapshot1.ranked_actions]
    expected_sequence = [
        "obtain_exposure",
        "clip_vessel",
        "convert_approach",
        "suction_field",
        "repair_injury",
        "improve_perfusion",
        "call_assistance",
    ]
    assert action_ids == expected_sequence

    # 4. Contingency plans – three canonical triggers are present.
    triggers = {cp.trigger_condition for cp in snapshot1.contingency_plans}
    assert triggers == {"hemorrhage_worsens", "hypoxia_worsens", "instability_worsens"}

    # 5. Simulation preview deterministic hash remains stable.
    assert (
        snapshot1.simulation_preview.deterministic_hash
        == snapshot2.simulation_preview.deterministic_hash
    )
