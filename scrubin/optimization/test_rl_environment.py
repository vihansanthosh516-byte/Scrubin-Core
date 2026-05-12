from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.optimization.rl.environment import ScrubInRLEnvironment
from scrubin.optimization.rl.action_space import ClinicalAction

def test_rl_environment():
    print("--- Phase 15.2: RL Environment Adapter Integration Test ---")
    
    # 1. Initialize Kernel and Environment
    kernel = ControlPlaneKernel(core_interface=None)
    env = ScrubInRLEnvironment(kernel)
    
    # 2. Reset Environment
    print("\n[Env] Resetting environment...")
    obs = env.reset()
    print(f"  - Initial Observation: {obs}")
    
    # 3. Test: Valid Action
    print("\n[Step 1] Applying action: ADMINISTER_OXYGEN")
    action = ClinicalAction("ADMINISTER_OXYGEN", value=10.0)
    obs, reward, done, info = env.step(action)
    print(f"  - Reward: {reward:.2f}")
    print(f"  - Done: {done}")
    print(f"  - Stability Index: {info.get('calibration', {}).get('global_stability_index')}")
    
    # 4. Test: Stability Invariant (Manual Trigger)
    print("\n[Step 2] Testing Calibration Hard Stop (Simulating failure)...")
    # We'll manually inject an 'Unrealistic' event via the kernel to trip the validator
    from scrubin.control_plane.streaming.channels import Topics
    kernel.event_stream.publish(
        Topics.PATIENT_VITALS, 
        {"category": "CLINICAL", "spo2": 10}, # Impossible vitals
        tick=10, 
        session_id=env.session_id
    )
    
    # Next step should trigger calibration failure and termination
    obs, reward, done, info = env.step(ClinicalAction("OBSERVE"))
    print(f"  - Reward (Penalty): {reward:.2f}")
    print(f"  - Done (Terminated): {done}")
    print(f"  - Failure Reason: {info.get('reason')}")

    print("\n--- Phase 15.2 RL Environment Test Complete ---")

if __name__ == "__main__":
    test_rl_environment()
