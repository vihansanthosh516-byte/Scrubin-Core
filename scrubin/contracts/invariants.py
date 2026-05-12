from scrubin.contracts.simulation import SimulationInvariant
from scrubin.world.model import SimulationWorld


def _spo2_bounds(world: SimulationWorld) -> bool:
    spo2 = world.physiology.vitals.get("spo2", 0)
    return 0 <= spo2 <= 100


def _heart_rate_bounds(world: SimulationWorld) -> bool:
    hr = world.physiology.vitals.get("heart_rate", 0)
    return 0 <= hr <= 300


def _bp_systolic_nonneg(world: SimulationWorld) -> bool:
    return world.physiology.vitals.get("bp_systolic", 0) >= 0


def _bp_diastolic_nonneg(world: SimulationWorld) -> bool:
    return world.physiology.vitals.get("bp_diastolic", 0) >= 0


def _organ_health_bounds(world: SimulationWorld) -> bool:
    organs = [
        world.organ_state.cardiovascular,
        world.organ_state.respiratory,
        world.organ_state.renal,
        world.organ_state.neurologic,
        world.organ_state.hematologic,
    ]
    return all(0.0 <= o.health <= 1.0 for o in organs)


def _resource_available_nonneg(world: SimulationWorld) -> bool:
    return all(r.available >= 0 for r in world.resource_manager.resources.values())


def _resource_reserved_nonneg(world: SimulationWorld) -> bool:
    for r in world.resource_manager.resources.values():
        if hasattr(r, "reserved"):
            if r.reserved < 0:
                return False
    return True


def _reserved_leq_capacity(world: SimulationWorld) -> bool:
    for r in world.resource_manager.resources.values():
        if hasattr(r, "reserved"):
            if r.reserved > r.total_capacity:
                return False
    return True


def _no_double_allocation(world: SimulationWorld) -> bool:
    if not hasattr(world, "_transaction_manager") or world._transaction_manager is None:
        return True
    tm = world._transaction_manager
    if not hasattr(tm, "_reservations"):
        return True
    ventilator_holders = {}
    for res in tm._reservations.values():
        if res.resource_type == "ventilators" and res.is_active:
            pid = res.patient_id
            if pid in ventilator_holders:
                return False
            ventilator_holders[pid] = res.id
    return True


def _mortality_monotonicity(world: SimulationWorld) -> bool:
    if not hasattr(world, "_prev_mortality_risk"):
        return True
    organs_collapsed = any(
        o.health < 0.3
        for o in [
            world.organ_state.cardiovascular,
            world.organ_state.respiratory,
            world.organ_state.renal,
        ]
    )
    spo2 = world.physiology.vitals.get("spo2", 100)
    sustained_hypoxia = spo2 < 85

    sys = world.physiology.vitals.get("bp_systolic", 120)
    dia = world.physiology.vitals.get("bp_diastolic", 80)
    map_val = (sys + 2 * dia) / 3.0
    sustained_shock = map_val < 60

    if organs_collapsed or sustained_hypoxia or sustained_shock:
        return world.mortality_risk >= world._prev_mortality_risk - 0.001

    return True


def _planner_utility_finite(world: SimulationWorld) -> bool:
    if not hasattr(world, "_last_planning_utility"):
        return True
    u = world._last_planning_utility
    import math
    return not math.isnan(u) and not math.isinf(u)


CANONICAL_INVARIANTS: list[SimulationInvariant] = [
    SimulationInvariant(
        id="physio.spo2_bounds",
        description="Oxygen saturation must be in [0, 100]",
        severity="error",
        evaluator=_spo2_bounds,
    ),
    SimulationInvariant(
        id="physio.heart_rate_bounds",
        description="Heart rate must be in [0, 300]",
        severity="error",
        evaluator=_heart_rate_bounds,
    ),
    SimulationInvariant(
        id="physio.bp_systolic_nonneg",
        description="Systolic blood pressure must be non-negative",
        severity="error",
        evaluator=_bp_systolic_nonneg,
    ),
    SimulationInvariant(
        id="physio.bp_diastolic_nonneg",
        description="Diastolic blood pressure must be non-negative",
        severity="error",
        evaluator=_bp_diastolic_nonneg,
    ),
    SimulationInvariant(
        id="physio.organ_health_bounds",
        description="All organ health values must be in [0.0, 1.0]",
        severity="fatal",
        evaluator=_organ_health_bounds,
    ),
    SimulationInvariant(
        id="resource.available_nonneg",
        description="All resource available counts must be non-negative",
        severity="error",
        evaluator=_resource_available_nonneg,
    ),
    SimulationInvariant(
        id="resource.reserved_nonneg",
        description="All resource reserved counts must be non-negative",
        severity="error",
        evaluator=_resource_reserved_nonneg,
    ),
    SimulationInvariant(
        id="resource.reserved_leq_capacity",
        description="Reservations must never exceed total capacity",
        severity="fatal",
        evaluator=_reserved_leq_capacity,
    ),
    SimulationInvariant(
        id="resource.no_double_allocation",
        description="One ventilator cannot belong to two patients simultaneously",
        severity="fatal",
        evaluator=_no_double_allocation,
    ),
    SimulationInvariant(
        id="mortality.monotonicity",
        description="Mortality risk cannot decrease under organ collapse, hypoxia, or shock",
        severity="error",
        evaluator=_mortality_monotonicity,
    ),
    SimulationInvariant(
        id="planner.utility_finite",
        description="MCTS utility must be finite (not NaN or inf)",
        severity="fatal",
        evaluator=_planner_utility_finite,
    ),
]


def register_invariant(invariant: SimulationInvariant) -> None:
    CANONICAL_INVARIANTS.append(invariant)


def _queue_procedure_uniqueness(world: SimulationWorld) -> bool:
    if not hasattr(world, "_scheduled_procedures"):
        return True
    ids = [p.id for p in world._scheduled_procedures]
    return len(ids) == len(set(ids))


def _queue_ticks_remaining_nonneg(world: SimulationWorld) -> bool:
    if not hasattr(world, "_scheduled_procedures"):
        return True
    return all(p.ticks_remaining >= 0 for p in world._scheduled_procedures)


def _queue_no_completed(world: SimulationWorld) -> bool:
    if not hasattr(world, "_scheduled_procedures"):
        return True
    return all(p.ticks_remaining > 0 for p in world._scheduled_procedures)


QUEUE_INVARIANTS: list[SimulationInvariant] = [
    SimulationInvariant(
        id="queue.procedure_uniqueness",
        description="Scheduled procedure IDs must be unique",
        severity="error",
        evaluator=_queue_procedure_uniqueness,
    ),
    SimulationInvariant(
        id="queue.ticks_remaining_nonneg",
        description="Scheduled procedure ticks_remaining must be non-negative",
        severity="error",
        evaluator=_queue_ticks_remaining_nonneg,
    ),
    SimulationInvariant(
        id="queue.no_completed_in_queue",
        description="No completed procedure (ticks_remaining=0) should remain in queue",
        severity="warn",
        evaluator=_queue_no_completed,
    ),
]


HOSPITAL_INVARIANTS: list[SimulationInvariant] = []

try:
    from scrubin.world.hospital import HospitalWorld

    def _patient_uniqueness(world: object) -> bool:
        if not isinstance(world, HospitalWorld):
            return True
        return len(world.patients) == len(set(world.patients.keys()))

    def _icu_occupancy(world: object) -> bool:
        if not isinstance(world, HospitalWorld):
            return True
        icu = world.resources.resources.get("icu_beds")
        if icu is None:
            return True
        return icu.currently_used <= icu.total_capacity

    HOSPITAL_INVARIANTS = [
        SimulationInvariant(
            id="world.patient_uniqueness",
            description="Patient IDs must be unique globally",
            severity="fatal",
            evaluator=_patient_uniqueness,
        ),
        SimulationInvariant(
            id="world.icu_occupancy",
            description="ICU occupied beds must not exceed total",
            severity="error",
            evaluator=_icu_occupancy,
        ),
    ]
except ImportError:
    pass
