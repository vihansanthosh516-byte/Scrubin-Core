import time
from scrubin.world.hospital import HospitalWorld
from scrubin.decision.hierarchical.planner import HierarchicalPlanner
from scrubin.communication.engine import CommunicationEngine
from scrubin.communication.models import Message, CommunicationChannel, MessagePriority
from scrubin.agents.teams.roles import AttendingPhysicianAgent, ResidentAgent, NurseAgent
from scrubin.agents.teams.coordination import TeamCoordinationEngine
from scrubin.population.models import PopulationGenerator
from scrubin.learning.online import OnlineLearner
from scrubin.governance.engine import GovernanceEngine
from scrubin.runtime.vectorized.engine import VectorizedSimulation
from scrubin.world_models.latent import LatentWorldModel
from scrubin.validation.scientific.validator import ScientificValidator

def run_phase_11_demo():
    print("--- Phase 11: Adaptive Clinical Intelligence & Autonomous Operations ---")
    
    # 1. Initialize the World & Population
    print("\n[Population] Generating Longitudinal Patient Cohort...")
    pop_gen = PopulationGenerator()
    patients = [pop_gen.generate_patient("elderly_frail") for _ in range(5)]
    print(f"  - Generated {len(patients)} patients with complex comorbidities.")
    
    print("\n[System] Initializing Hospital World...")
    world = HospitalWorld()
    
    # 2. Initialize the Hierarchical Planner
    print("[System] Initializing Hierarchical Planner...")
    planner = HierarchicalPlanner(world)
    
    # 3. Initialize Communication & Teams
    print("[System] Setting up Autonomous Clinical Team...")
    comms = CommunicationEngine(failure_rate=0.05)
    team = TeamCoordinationEngine(comms)
    
    attending = AttendingPhysicianAgent("dr_smith")
    resident = ResidentAgent("dr_jones")
    nurse = NurseAgent("nurse_kelly")
    
    team.add_agent(attending)
    team.add_agent(resident, supervisor_id="dr_smith")
    team.add_agent(nurse, supervisor_id="dr_jones")
    
    # 4. Initialize Learning & Governance
    print("[Governance] Initializing Hospital Governance & Online Learning...")
    governance = GovernanceEngine()
    learner = OnlineLearner()
    
    # 5. Initialize High-Performance Runtime & World Models
    print("[Runtime] Booting Vectorized Simulation Engine (10,000 patients)...")
    vec_sim = VectorizedSimulation(num_patients=10000)
    world_model = LatentWorldModel()
    
    # 6. Simulate a Planning Cycle
    print("\n[Planner] Executing Multi-Timescale Planning...")
    hierarchical_results = planner.plan()
    for timescale, result in hierarchical_results.items():
        print(f"  - {timescale.name} Layer: Selected Action = {result.selected_action}")
    
    # 7. Simulate Team Communication & Adaptation
    print("\n[Team] Simulating Clinical Communication & Policy Adaptation...")
    
    # Hospital load increases
    governance.adapt_policy(hospital_load=0.95)
    print(f"  - Governance adapted: Triage Threshold = {governance.current_policy.triage_threshold}")
    
    # Nurse pales resident
    msg1 = nurse.communicate("dr_jones", "P1 SpO2 84%.", CommunicationChannel.PAGER, MessagePriority.STAT)
    comms.send_message(msg1)
    
    comms.process_tick()
    messages = comms.get_new_messages_for_agent("dr_jones")
    for msg in messages:
        print(f"  - {resident.role} received: '{msg.content}'")
        # Learner updates based on outcome (simulated)
        learner.update_policy("intubation", outcome_utility=0.9)
        
    # 8. Scientific Validation
    print("\n[Validation] Running Scientific Realism Check...")
    validator = ScientificValidator()
    val_result = validator.validate_outcome_distribution([0.35, 0.42, 0.38], "septic_shock_mortality")
    print(f"  - Septic Shock Mortality Check: {val_result['passed']} (Mean: {val_result['actual_mean']:.2f})")

    print("\n--- Phase 11 Full System Demo Complete ---")

if __name__ == "__main__":
    try:
        run_phase_11_demo()
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        run_phase_11_demo()
    except Exception as e:
        print(f"Demo failed (expected if some dependencies are missing): {e}")
