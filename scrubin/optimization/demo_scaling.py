from scrubin.optimization.scaling.distributed.deterministic_cluster import DeterministicCluster
from scrubin.optimization.scaling.rollout.worker import RolloutWorker
from scrubin.optimization.scaling.rollout.coordinator import RolloutCoordinator
from scrubin.optimization.scaling.curriculum.scheduler import CurriculumScheduler
from scrubin.optimization.scaling.training.dataset_builder import DatasetBuilder

class MockPolicy:
    def act(self, obs, seed):
        # Deterministic mock action
        return {"type": "OBSERVE", "seed": seed}

class MockEnv:
    def __init__(self, seed):
        self.seed = seed
        self.t = 0
    def reset(self):
        self.t = 0
        return {"obs": "start"}
    def step(self, action):
        self.t += 1
        return {"obs": "step"}, 0.1, self.t >= 2, {}

def run_phase_15_4_demo():
    print("--- Phase 15.4: Scaling + Deterministic Training Architecture ---")
    
    # 1. Setup Cluster and Coordinator
    base_seed = 42
    cluster = DeterministicCluster(base_seed)
    
    def env_factory(seed): return MockEnv(seed)
    workers = [RolloutWorker(env_factory, i) for i in range(3)]
    coordinator = RolloutCoordinator(cluster, workers)
    
    policy = MockPolicy()
    
    # 2. Run Deterministic Rollouts
    print("\n[Rollout] Dispatching distributed policy to 3 workers...")
    traces_run_1 = coordinator.dispatch(policy)
    
    # 3. Verification: Deterministic Identity
    print("\n[Verification] Rerunning with same base seed...")
    cluster_2 = DeterministicCluster(base_seed)
    coordinator_2 = RolloutCoordinator(cluster_2, workers)
    traces_run_2 = coordinator_2.dispatch(policy)
    
    # Compare first step of first worker
    match = (traces_run_1[0] == traces_run_2[0])
    print(f"  - Bit-Identical Distributed Trace: {'MATCHED' if match else 'DIVERGED'}")
    
    # 4. Dataset Building
    print("\n[Training] Normalizing distributed traces into training dataset...")
    builder = DatasetBuilder()
    dataset = builder.build(traces_run_1)
    print(f"  - Total Samples Collected: {len(dataset)}")
    
    # 5. Curriculum Stability
    print("\n[Curriculum] Updating difficulty based on scientific stability...")
    scheduler = CurriculumScheduler(start_difficulty=0.5)
    print(f"  - Current Difficulty: {scheduler.get_difficulty()}")
    
    print("  - Injecting High Pass Rate (0.98)...")
    scheduler.update({"calibration_pass_rate": 0.98})
    print(f"  - New Difficulty: {scheduler.get_difficulty()} (Increased)")
    
    print("  - Injecting Low Pass Rate (0.75)...")
    scheduler.update({"calibration_pass_rate": 0.75})
    print(f"  - New Difficulty: {scheduler.get_difficulty()} (Decreased for stability)")

    print("\n--- Phase 15.4 Scaling Architecture Demo Complete ---")

if __name__ == "__main__":
    run_phase_15_4_demo()
