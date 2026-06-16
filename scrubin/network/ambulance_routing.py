"""Deterministic ambulance routing for the multi‑hospital network.

The module provides a lightweight graph representation of hospitals and a Dijkstra‑
based shortest‑path algorithm that breaks ties alphabetically (by ``hospital_id``).
All travel times are expressed in simulation ticks and derived from the
geographic distance between hospitals when that information is present in the
``extra`` field of a :class:`~scrubin.network.hospital_registry.HospitalConfig`.
If location data is missing, a travel time of ``0`` is used – this keeps the
implementation deterministic without external data.
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from .hospital_registry import HospitalRegistry, HospitalConfig
from .transfer_engine import TransferRequest  # noqa: F401 – imported for typing only


def _hash_sha256(text: str) -> str:
    """Return a deterministic SHA‑256 hex digest of *text*.

    Used for deterministic IDs on routes and ambulances.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great‑circle distance in kilometres between two points.

    Simple implementation sufficient for deterministic routing.  The earth
    radius is fixed at 6371 km.
    """
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _travel_ticks(distance_km: float, speed_kmh: float = 80.0) -> int:
    """Convert a distance to simulation ticks.

    The conversion assumes a fixed speed (default 80 km/h) and a tick duration
    of 1 minute.  ``ticks = round((distance / speed) * 60)`` yields an integer.
    """
    if speed_kmh <= 0:
        return 0
    minutes = (distance_km / speed_kmh) * 60.0
    return max(1, int(round(minutes)))  # minimum of 1‑tick travel


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(registry: HospitalRegistry) -> Dict[str, List[Tuple[str, int]]]:
    """Create an adjacency list for the hospital network.

    The returned mapping is ``{origin_hospital_id: [(dest_id, travel_ticks), ...]}``.
    The graph is fully connected (edges in both directions).  If location data
    is missing for a hospital, travel time defaults to ``0`` which still
    yields a deterministic path.
    """
    graph: Dict[str, List[Tuple[str, int]]] = {cfg.hospital_id: [] for cfg in registry}
    # Pre‑extract coordinates for speed.
    coords: Dict[str, Tuple[float, float]] = {}
    for cfg in registry:
        loc = cfg.extra.get("location") if isinstance(cfg.extra, dict) else None
        if loc and isinstance(loc, dict) and "lat" in loc and "lon" in loc:
            try:
                lat = float(loc["lat"])
                lon = float(loc["lon"])
                coords[cfg.hospital_id] = (lat, lon)
            except (TypeError, ValueError):
                # Invalid numeric conversion – treat as missing.
                pass
    for origin in registry:
        oid = origin.hospital_id
        for dest in registry:
            did = dest.hospital_id
            if oid == did:
                continue
            # Determine travel time.
            if oid in coords and did in coords:
                distance = _haversine(*coords[oid], *coords[did])
                travel = _travel_ticks(distance)
            else:
                travel = 0
            graph[oid].append((did, travel))
        # Sort adjacency list deterministically – alphabetical by destination ID.
        graph[oid].sort(key=lambda pair: pair[0])
    return graph


# ---------------------------------------------------------------------------
# Ambulance unit model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AmbulanceRoute:
    """Immutable descriptor of a pre‑computed route.

    * origin – Source hospital ID.
    * destination – Target hospital ID.
    * travel_time_ticks – Total travel duration.
    * path – Ordered list of intermediate hospital IDs (including origin and
      destination).  For a direct edge the path contains just the two IDs.
    """

    origin: str
    destination: str
    travel_time_ticks: int
    path: Tuple[str, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ID is a hash of the concatenated route description.
        text = f"{self.origin}|{self.destination}|{self.travel_time_ticks}|{'-'.join(self.path)}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


@dataclass(frozen=True, slots=True)
class AmbulanceUnit:
    """Immutable ambulance representation.

    * ambulance_id – Deterministic identifier.
    * current_location – Hospital ID where the unit is currently stationed.
    * status – ``available`` or ``en_route``.
    * assigned_route – Optional ``AmbulanceRoute`` when the unit is in transit.
    * ticks_remaining – Ticks left until arrival (0 if available).
    """

    ambulance_id: str
    current_location: str
    status: str = "available"
    assigned_route: Optional[AmbulanceRoute] = None
    ticks_remaining: int = 0
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.ambulance_id}|{self.current_location}|{self.status}|{self.ticks_remaining}"
        object.__setattr__(self, "deterministic_id", _hash_sha256(text))


@dataclass(slots=True)
class AmbulanceStore:
    """Append‑only store of all ambulance units in the network.

    The store is deliberately mutable – new units may be added at runtime –
    but existing entries are never removed to preserve replay integrity.
    """

    units: List[AmbulanceUnit] = field(default_factory=list)

    def add(self, unit: AmbulanceUnit) -> None:
        """Append a new ambulance unit to the store.

        The method does **not** check for duplicates; callers are responsible for
        ensuring deterministic creation order.
        """
        self.units.append(unit)

    def get_available(self, location: str) -> List[AmbulanceUnit]:
        """Return a deterministic list of available ambulances at *location*.

        The list is sorted by ``ambulance_id`` to guarantee reproducible selection.
        """
        available = [u for u in self.units if u.status == "available" and u.current_location == location]
        available.sort(key=lambda u: u.ambulance_id)
        return available

    def update_progress(self) -> List[AmbulanceUnit]:
        """Advance the state of all en‑route ambulances by one tick.

        Returns a list of ambulances that have arrived at their destination
        during this tick (i.e., ``ticks_remaining`` reaches ``0``).
        """
        arrived: List[AmbulanceUnit] = []
        for i, unit in enumerate(self.units):
            if unit.status != "en_route":
                continue
            # Decrement remaining ticks.
            new_ticks = unit.ticks_remaining - 1
            if new_ticks <= 0:
                # Arrival – transition to ``available`` at the destination.
                new_unit = AmbulanceUnit(
                    ambulance_id=unit.ambulance_id,
                    current_location=unit.assigned_route.destination,  # type: ignore[arg-type]
                    status="available",
                    assigned_route=None,
                    ticks_remaining=0,
                )
                arrived.append(new_unit)
                self.units[i] = new_unit
            else:
                # Still travelling.
                new_unit = AmbulanceUnit(
                    ambulance_id=unit.ambulance_id,
                    current_location=unit.current_location,
                    status="en_route",
                    assigned_route=unit.assigned_route,
                    ticks_remaining=new_ticks,
                )
                self.units[i] = new_unit
        return arrived


# ---------------------------------------------------------------------------
# Dispatch logic – creates a TransferRequest and assigns an ambulance if possible.
# ---------------------------------------------------------------------------

def dispatch(
    patient_id: str,
    origin_id: str,
    destination_id: str,
    store: AmbulanceStore,
    graph: Dict[str, List[Tuple[str, int]]],
    priority: int = 0,
) -> TransferRequest:
    """Create a deterministic ``TransferRequest`` for a patient.

    The function performs the following steps deterministically:

    1. Compute the shortest path (in ticks) between *origin_id* and
       *destination_id* using Dijkstra with alphabetical tie‑breaks.
    2. Look for the first available ambulance at the origin (sorted by
       ``ambulance_id``).  If one exists, assign it to the request and update its
       status to ``en_route``.
    3. Return a :class:`TransferRequest` instance with appropriate fields.
    """
    # Compute shortest path.
    path, travel_ticks = _shortest_path(origin_id, destination_id, graph)
    route = AmbulanceRoute(
        origin=origin_id,
        destination=destination_id,
        travel_time_ticks=travel_ticks,
        path=tuple(path),
    )
    # Find an available ambulance.
    available_units = store.get_available(origin_id)
    if available_units:
        ambulance = available_units[0]
        # Update the unit in the store to be en_route.
        # Since ``AmbulanceStore`` is mutable, we replace the matching entry.
        for idx, unit in enumerate(store.units):
            if unit.ambulance_id == ambulance.ambulance_id:
                store.units[idx] = AmbulanceUnit(
                    ambulance_id=unit.ambulance_id,
                    current_location=unit.current_location,
                    status="en_route",
                    assigned_route=route,
                    ticks_remaining=travel_ticks,
                )
                break
        assigned_id = ambulance.ambulance_id
    else:
        assigned_id = ""
    # Build the TransferRequest – defined in ``transfer_engine``.
    return TransferRequest(
        patient_id=patient_id,
        origin=origin_id,
        destination=destination_id,
        request_time=0,  # Placeholder – callers should set the actual tick.
        priority=priority,
        status="assigned" if assigned_id else "pending",
        assigned_ambulance=assigned_id,
    )


def _shortest_path(
    origin: str,
    destination: str,
    graph: Dict[str, List[Tuple[str, int]]],
) -> Tuple[List[str], int]:
    """Return the shortest path and total travel time using Dijkstra.

    The algorithm breaks ties by preferring the lexicographically smallest
    ``hospital_id`` at each step, ensuring deterministic results.
    """
    import heapq

    # Priority queue: (cumulative_ticks, hospital_id, path_list)
    heap: List[Tuple[int, str, List[str]]] = [(0, origin, [origin])]
    visited: Dict[str, int] = {}
    while heap:
        ticks, node, path = heapq.heappop(heap)
        if node in visited and visited[node] <= ticks:
            continue
        visited[node] = ticks
        if node == destination:
            return path, ticks
        for neighbor, travel in graph.get(node, []):
            new_ticks = ticks + travel
            # Only push if we have not visited with a better cost.
            if neighbor not in visited or new_ticks < visited[neighbor]:
                # Deterministic ordering: heapq already orders tuples; using
                # ``neighbor`` as the second element provides alphabetical tie‑break.
                heapq.heappush(heap, (new_ticks, neighbor, path + [neighbor]))
    # No path (should not happen in a fully connected graph). Return direct.
    return [origin, destination], 0
