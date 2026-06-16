"""Data models for the complications core.
+
+All models are frozen dataclasses to guarantee immutability.  ``replace`` from
+``dataclasses`` is used for updates, ensuring no deep‑copy or mutable state is
+introduced.  Deterministic ordering and hashing are provided via tuple‑based
+fields.
+"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Tuple


@dataclass(frozen=True, slots=True)
class Complication:
    """Immutable representation of a single complication.
+
+    Fields are deliberately simple and hashable.  ``physiology_delta`` and
+    ``anatomy_delta`` are opaque payloads supplied by the caller – they must be
+    hashable for deterministic hashing.
+    """

    deterministic_id: int
    complication_type: str
    affected_structure: str
    severity: int
    progression_stage: str
    activation_tick: int
    last_update_tick: int
    active: bool
    resolved: bool
    physiology_delta: Any
    anatomy_delta: Any
    metadata: Any

    def advance_stage(self, new_stage: str, tick: int, severity: int | None = None) -> "Complication":
        """Return a new instance with an updated progression stage.
+
+        ``severity`` may be adjusted; if omitted the existing value is kept.
+        """

        return replace(
            self,
            progression_stage=new_stage,
            last_update_tick=tick,
            severity=severity if severity is not None else self.severity,
        )

    def resolve(self, tick: int) -> "Complication":
        """Mark the complication as resolved at ``tick``.
+        """

        return replace(
            self,
            resolved=True,
            active=False,
            last_update_tick=tick,
        )

    def deactivate(self, tick: int) -> "Complication":
        """Deactivate without resolving (e.g., temporary pause)."""

        return replace(self, active=False, last_update_tick=tick)


@dataclass(frozen=True, slots=True)
class ComplicationEvent:
    """Immutable event emitted by the manager.
+
+    ``event_type`` is a short string such as ``"activated"`` or ``"resolved"``.
+    ``complication_id`` references the associated complication.
+    """

    tick: int
    event_type: str
    complication_id: int
    details: Any = None


@dataclass(frozen=True, slots=True)
class ComplicationState:
    """Container tracking the deterministic state of all complications.
+
+    ``active_complications`` and ``resolved_complications`` are stored as
+    *sorted* tuples to guarantee deterministic ordering regardless of insertion
+    order.  The ``deterministic_hash`` is a simple hash over the tuple of ids –
+    this remains stable across runs because all constituent objects are frozen
+    and hash‑stable.
+    """

    active_complications: Tuple[Complication, ...] = ()
    resolved_complications: Tuple[Complication, ...] = ()
    deterministic_hash: int = 0

    def _recalc_hash(self) -> int:
        # Deterministic hash based on deterministic_id ordering
        active_ids = tuple(c.deterministic_id for c in self.active_complications)
        resolved_ids = tuple(c.deterministic_id for c in self.resolved_complications)
        return hash((active_ids, resolved_ids))

    def with_updates(
        self,
        *,
        add_active: Tuple[Complication, ...] | None = None,
        remove_active_ids: Tuple[int, ...] | None = None,
        add_resolved: Tuple[Complication, ...] | None = None,
    ) -> "ComplicationState":
        """Return a new state with the supplied modifications applied.
+
+        All collections are kept sorted by ``deterministic_id``.
+        """

        active = list(self.active_complications)
        resolved = list(self.resolved_complications)

        if add_active:
            active.extend(add_active)
        if remove_active_ids:
            active = [c for c in active if c.deterministic_id not in set(remove_active_ids)]
        if add_resolved:
            resolved.extend(add_resolved)

        # Sort for deterministic ordering
        active.sort(key=lambda c: c.deterministic_id)
        resolved.sort(key=lambda c: c.deterministic_id)

        new_state = replace(
            self,
            active_complications=tuple(active),
            resolved_complications=tuple(resolved),
        )
        # Recalculate hash
        return replace(new_state, deterministic_hash=new_state._recalc_hash())

*** End Patch
PATCH