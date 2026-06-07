"""Snapshot storage for deterministic replay.

A snapshot is a full ``WorldState`` serialized as JSON. Snapshots are taken
periodically (e.g. every ``snapshot_interval`` ticks) and stored alongside the
event log. Rebuilding a session consists of loading the latest snapshot and
replaying subsequent events.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Optional

from scrubin.world.state import WorldState


class SnapshotStore:
    """File‑system based snapshot store.

    In a real deployment this could be backed by object storage (S3, GCS) or a
    database. For now we persist snapshots under ``base_dir`` using the session
    identifier as the filename.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        if base_dir is None:
            base_dir = os.path.join(os.getcwd(), "scrubin", "snapshots")
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        return os.path.join(self.base_dir, f"{session_id}.json")

    def save_snapshot(self, session_id: str, world: WorldState) -> None:
        path = self._path(session_id)
        # ``WorldState`` is already JSON‑serialisable via its ``asdict`` representation.
        data = json.dumps(asdict(world), sort_keys=True, separators=(",", ":"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def load_snapshot(self, session_id: str) -> Optional[WorldState]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # ``WorldState`` can be reconstructed via the existing deserialization utilities.
        from scrubin.api.serialization import deserialize_worldstate

        return deserialize_worldstate(json.dumps(data))
