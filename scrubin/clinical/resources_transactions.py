import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class ReservationStatus(Enum):
    PENDING = "pending"
    RESERVED = "reserved"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"


@dataclass
class ResourceReservation:
    id: str
    resource_type: str
    amount: int
    holder_id: str
    patient_id: str
    status: ReservationStatus = ReservationStatus.PENDING
    tick_created: int = 0
    tick_expires: int = 0

    @property
    def is_active(self) -> bool:
        return self.status in (
            ReservationStatus.PENDING,
            ReservationStatus.RESERVED,
        )

    @property
    def is_consumed(self) -> bool:
        return self.status in (ReservationStatus.COMMITTED, ReservationStatus.EXPIRED)


@dataclass
class TransactionLog:
    reservations: List[ResourceReservation] = field(default_factory=list)
    committed: List[ResourceReservation] = field(default_factory=list)
    released: List[ResourceReservation] = field(default_factory=list)


class TransactionalResourceManager:
    def __init__(self, base_manager=None, tick: int = 0):
        self._base = base_manager
        self._reservations: Dict[str, ResourceReservation] = {}
        self._tick = tick
        self._log = TransactionLog()

        if base_manager:
            self._reserved_amounts = {res_id: 0 for res_id in base_manager.resources}
        else:
            self._reserved_amounts = {
                "ventilators": 0,
                "icu_beds": 0,
                "blood_units": 0,
                "staff_bandwidth": 0,
            }

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_lock", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = threading.Lock()

    @property
    def resources(self):
        if self._base:
            return self._base.resources
        return {}

    def _ensure_lock(self):
        if not hasattr(self, "_lock"):
            self._lock = threading.Lock()

    def set_tick(self, tick: int):
        self._tick = tick

    def available_after_reservations(self, resource_type: str) -> int:
        base_state = self.resources.get(resource_type)
        if base_state is None:
            return 0
        reserved = self._reserved_amounts.get(resource_type, 0)
        return base_state.available - reserved

    def request(
        self,
        resource_type: str,
        amount: int,
        holder_id: str,
        patient_id: str,
        ttl: int = 10,
    ) -> Optional[ResourceReservation]:
        self._ensure_lock()
        with self._lock:
            available = self.available_after_reservations(resource_type)
            if available < amount:
                return None

            reservation = ResourceReservation(
                id=f"res-{uuid4().hex[:8]}",
                resource_type=resource_type,
                amount=amount,
                holder_id=holder_id,
                patient_id=patient_id,
                status=ReservationStatus.RESERVED,
                tick_created=self._tick,
                tick_expires=self._tick + ttl,
            )

            self._reservations[reservation.id] = reservation
            self._reserved_amounts[resource_type] = (
                self._reserved_amounts.get(resource_type, 0) + amount
            )
            self._log.reservations.append(reservation)
            return reservation

    def commit(self, reservation_id: str) -> bool:
        self._ensure_lock()
        with self._lock:
            res = self._reservations.get(reservation_id)
            if res is None or res.status != ReservationStatus.RESERVED:
                return False

            base_state = self.resources.get(res.resource_type)
            if base_state and base_state.available >= res.amount:
                base_state.consume(res.amount)
                res.status = ReservationStatus.COMMITTED
                self._reserved_amounts[res.resource_type] = max(
                    0, self._reserved_amounts.get(res.resource_type, 0) - res.amount
                )
                self._log.committed.append(res)
                return True
            return False

    def release(self, reservation_id: str) -> bool:
        self._ensure_lock()
        with self._lock:
            res = self._reservations.get(reservation_id)
            if res is None:
                return False

            if res.status == ReservationStatus.RESERVED:
                self._reserved_amounts[res.resource_type] = max(
                    0, self._reserved_amounts.get(res.resource_type, 0) - res.amount
                )
                res.status = ReservationStatus.RELEASED
                self._log.released.append(res)
                return True

            if res.status == ReservationStatus.COMMITTED:
                base_state = self.resources.get(res.resource_type)
                if base_state:
                    base_state.release(res.amount)
                res.status = ReservationStatus.RELEASED
                self._log.released.append(res)
                return True

            return False

    def expire_stale(self, current_tick: int):
        self._ensure_lock()
        with self._lock:
            for res in list(self._reservations.values()):
                if (
                    res.status == ReservationStatus.RESERVED
                    and current_tick >= res.tick_expires
                ):
                    self._reserved_amounts[res.resource_type] = max(
                        0,
                        self._reserved_amounts.get(res.resource_type, 0) - res.amount,
                    )
                    res.status = ReservationStatus.EXPIRED

    def request_intervention_resources(
        self,
        procedure_id: str,
        holder_id: str,
        patient_id: str,
        ttl: int = 10,
    ) -> Optional[str]:
        requirements = {}
        if procedure_id in ("intubation", "ventilator_support"):
            requirements = {"ventilators": 1, "staff_bandwidth": 15}
        elif procedure_id == "blood_transfusion":
            requirements = {"blood_units": 2, "staff_bandwidth": 10}
        elif procedure_id == "surgical_intervention":
            requirements = {"icu_beds": 1, "staff_bandwidth": 40}
        else:
            return None

        reservations = []
        for res_type, amount in requirements.items():
            res = self.request(res_type, amount, holder_id, patient_id, ttl)
            if res is None:
                for r in reservations:
                    self.release(r.id)
                return None
            reservations.append(res)

        return reservations[0].id if reservations else None

    def commit_intervention(self, reservation_id: str) -> bool:
        return self.commit(reservation_id)

    def get_reservation(self, reservation_id: str) -> Optional[ResourceReservation]:
        return self._reservations.get(reservation_id)

    @property
    def log(self) -> TransactionLog:
        return self._log
