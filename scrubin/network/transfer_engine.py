"""Deterministic transfer engine for patient relocation between hospitals.

The implementation follows the Phase 6.1 spec while staying lightweight.
All decisions are deterministic: pending requests are processed in a stable
order (by request_time then patient_id) and every decision is recorded with a
SHA‑256 based ID.
"""

import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# NOTE: ``HospitalSnapshot`` is defined in ``network_snapshot.py``.  To avoid a
# circular import we use a forward reference for type‑checking only.


def _hash_sha256(text: str) -> str:
    """Return a deterministic lower‑case SHA‑256 digest of *text*.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Transfer request / decision models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TransferRequest:
    """Immutable request to move a patient from one hospital to another.

    * patient_id – Unique identifier for the patient.
    * origin – Source hospital ID.
    * destination – Target hospital ID.
    * request_time – Simulation tick when the request was generated.
    * priority – Integer priority (higher → more urgent).
    * status – ``pending`` | ``assigned`` | ``rejected`` | ``completed``.
    * assigned_ambulance – ID of the ambulance handling the transfer (empty if none).
    """

    patient_id: str
    origin: str
    destination: str
    request_time: int
    priority: int = 0
    status: str = "pending"
    assigned_ambulance: str = ""
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.patient_id}|{self.origin}|{self.destination}|{self.request_time}|{self.priority}|{self.status}|{self.assigned_ambulance}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


@dataclass(frozen=True, slots=True)
class TransferDecision:
    """Result of evaluating a :class:`TransferRequest`.

    * request_id – Deterministic ID of the related request.
    * decision – ``accepted`` | ``rejected`` | ``deferred``.
    * reason – Human‑readable explanation.
    """

    request_id: str
    decision: str
    reason: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.request_id}|{self.decision}|{self.reason}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


@dataclass(frozen=True, slots=True)
class TransferDecisionEvent:
    """Event emitted when a transfer decision is made.

    * decision – The :class:`TransferDecision` instance.
    * tick – Simulation tick at which the decision occurred.
    """

    decision: TransferDecision
    tick: int
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.decision.deterministic_id}|{self.tick}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


# ---------------------------------------------------------------------------
# Transfer engine – processes pending requests
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TransferEngine:
    """Append‑only engine that evaluates transfer requests.

    The engine holds a list of pending :class:`TransferRequest` objects.  The
    ``process_requests`` method evaluates each request against the provided
    ``hospital_snapshots`` (a mapping of ``hospital_id`` to a snapshot object).
    For the minimal implementation we accept all requests unless the target
    hospital is unknown.
    """

    pending_requests: List[TransferRequest] = field(default_factory=list)

    def submit(self, request: TransferRequest) -> None:
        """Append a new request to the engine.
        """
        self.pending_requests.append(request)

    def process_requests(
        self,
        hospital_snapshots: Dict[str, "HospitalSnapshot"],
        current_tick: int,
    ) -> Tuple[List[TransferDecision], List[TransferDecisionEvent]]:
        """Process all pending requests deterministically.

        * Requests are sorted by ``request_time`` then ``patient_id`` to guarantee
          reproducibility.
        * If the destination hospital exists in ``hospital_snapshots`` the
          request is ``accepted``; otherwise it is ``rejected``.
        * The method returns a list of decisions and the corresponding events.
        """
        # Ensure deterministic ordering.
        self.pending_requests.sort(key=lambda r: (r.request_time, r.patient_id))
        decisions: List[TransferDecision] = []
        events: List[TransferDecisionEvent] = []
        for req in self.pending_requests:
            if req.destination in hospital_snapshots:
                decision = TransferDecision(
                    request_id=req.deterministic_id,
                    decision="accepted",
                    reason="Destination hospital available",
                )
            else:
                decision = TransferDecision(
                    request_id=req.deterministic_id,
                    decision="rejected",
                    reason="Destination hospital unknown",
                )
            decisions.append(decision)
            events.append(TransferDecisionEvent(decision=decision, tick=current_tick))
        # Clear pending requests – in a real system we would keep track of
        # in‑flight transfers, but for the deterministic stub we simply reset.
        self.pending_requests.clear()
        return decisions, events
