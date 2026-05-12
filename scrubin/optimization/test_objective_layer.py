from scrubin.optimization.objective.objective_builder import ObjectiveBuilder

def test_constrained_objective():
    print("--- Phase 15.1: Constrained Objective Layer Integration Test ---")
    builder = ObjectiveBuilder()
    
    # Test Case 1: High Success, High Realism (Green Light)
    print("\n[Scenario 1] High Clinical Success + Perfect Realism")
    reward_1 = builder.compute(
        trajectory=None, 
        outcome="SURVIVED", 
        realism_score=0.1, # Good score
        drift_report={"global_stability_index": 1.0, "worst_case_drift": 0.0}
    )
    print(f"  - Final Reward: {reward_1:.2f} (Target: > 0.5)")
    
    # Test Case 2: High Success, Broken Realism (Constraint Override)
    print("\n[Scenario 2] High Clinical Success + Broken Realism (REJECTED)")
    reward_2 = builder.compute(
        trajectory=None, 
        outcome="SURVIVED", 
        realism_score=0.9, # Bad score
        drift_report={"global_stability_index": 1.0, "worst_case_drift": 0.0}
    )
    print(f"  - Final Reward: {reward_2:.2f} (Target: < 0.0 due to constraint)")
    
    # Test Case 3: Clinical Failure
    print("\n[Scenario 3] Clinical Failure (Mortality)")
    reward_3 = builder.compute(
        trajectory=None, 
        outcome="DECEASED", 
        realism_score=0.1, 
        drift_report={"global_stability_index": 1.0}
    )
    print(f"  - Final Reward: {reward_3:.2f} (Target: < 0.0)")
    
    # Test Case 4: Stability Regression
    print("\n[Scenario 4] Success but Significant Stability Drift")
    reward_4 = builder.compute(
        trajectory=None, 
        outcome="SURVIVED", 
        realism_score=0.1, 
        drift_report={"global_stability_index": 0.7, "worst_case_drift": 0.15}
    )
    print(f"  - Final Reward: {reward_4:.2f} (Target: < reward_1 due to stability penalty)")

    print("\n--- Phase 15.1 Constrained Objective Test Complete ---")

if __name__ == "__main__":
    test_constrained_objective()
