from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.optimization.debug.trace_schema import EpisodeStepTrace
from scrubin.optimization.debug.episode_trace import EpisodeTrace
from scrubin.optimization.debug.causal_episode_linker import CausalEpisodeLinker
from scrubin.optimization.debug.failure_analyzer import FailureAnalyzer
from scrubin.optimization.debug.replay_bridge import ReplayBridge
from scrubin.control_plane.comparison.hash_state import StateHasher

def test_episode_debugging():
    print("--- Phase 15.3: RL Episode Causal Debugging Integration Test ---")
    
    # 1. Initialize Kernel and Debug Tools
    kernel = ControlPlaneKernel(core_interface=None)
    session_id = "debug-sess-1"
    trace = EpisodeTrace(session_id)
    linker = CausalEpisodeLinker()
    analyzer = FailureAnalyzer()
    bridge = ReplayBridge()
    
    # 2. Mock an RL Episode Step
    print("\n[Forensics] Logging RL Episode Step (Tick 10)...")
    # Simulate an action being applied to the engine
    from scrubin.optimization.rl.action_space import ClinicalAction
    action = ClinicalAction("ADMINISTER_OXYGEN")
    
    # Manually reconstruct the resulting state hash for the trace
    # (Using the kernel's current state as the 'mocked' result)
    result = kernel.replay.reconstruct_session(session_id)
    current_hash = StateHasher.hash_state(result["final_state"])
    
    step = EpisodeStepTrace(
        step_id=1,
        tick=10,
        action={"type": "ADMINISTER_OXYGEN"},
        observation={"vitals": {"spo2": 95}},
        reward=0.1,
        calibration_score=0.05,
        state_hash=current_hash
    )
    trace.log_step(step)
    
    # 3. Test: Causal Linkage
    print("\n[Linker] Linking RL Step to Causal Execution Graph...")
    links = linker.link(step, kernel.causal_graph)
    print(f"  - Causal Links Found: {len(links)}")
    
    # 4. Test: Failure Analysis
    print("\n[Analyzer] Performing semantic failure analysis...")
    analysis = analyzer.analyze(trace)
    print(f"  - Classification: {analysis['type']}")
    print(f"  - Explanation: {analysis.get('explanation', 'N/A')}")
    
    # 5. Test: Replay Bridge (State Verification)
    print("\n[Bridge] Verifying trace consistency via deterministic replay...")
    verification = bridge.verify_episode(trace, kernel)
    print(f"  - Bit-Identical Match: {verification['match']}")
    print(f"  - Final Hash: {verification['final_hash'][:12]}...")

    print("\n--- Phase 15.3 RL Episode Debugging Test Complete ---")

if __name__ == "__main__":
    test_episode_debugging()
