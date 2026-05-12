class Topics:
    # Patient State
    PATIENT_VITALS = "patient.vitals"
    PATIENT_TRAJECTORY = "patient.trajectory"
    
    # Execution & Planning
    MCTS_TRACE = "planner.mcts_trace"
    ARBITRATION = "planner.arbitration"
    IR_EXECUTION = "execution.ir_node"
    
    # Infrastructure & Health
    NODE_HEALTH = "cluster.node_health"
    RESOURCE_ALERTS = "cluster.resource_alerts"
    FAILOVER_EVENTS = "cluster.failover"
    
    # Clinical Events
    OUTBREAK_EVENTS = "clinical.outbreak"
    MORTALITY_EVENTS = "clinical.mortality"
    
    # Verification
    CONTRACT_VIOLATIONS = "verification.contract_violation"
    DIVERGENCE_ALERTS = "verification.divergence"
