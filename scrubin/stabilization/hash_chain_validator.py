"""Hash chain validator – builds a deterministic tick‑by‑tick hash chain.
All hashes are SHA‑256 of canonical JSON (sorted keys, no whitespace).
Only world_state_hash is populated; other component hashes are empty strings.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Tuple, List

from scrubin.core.orchestrator import Orchestrator
from scrubin.replay.hash import world_hash

# ---------------------------------------------------------------------------
# Frozen dataclass for a single tick entry
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class HashChainEntry:
    tick: int
    world_state_hash: str
    physiology_hash: str
    cognition_hash: str
    resource_hash: str
    agent_hash: str
    rl_snapshot_hash: str
    chain_hash: str          # hash of (previous chain_hash + canonical entry JSON)
    deterministic_id: str   # hash of tick + chain_hash

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "world_state_hash": self.world_state_hash,
            "physiology_hash": self.physiology_hash,
            "cognition_hash": self.cognition_hash,
            "resource_hash": self.resource_hash,
            "agent_hash": self.agent_hash,
            "rl_snapshot_hash": self.rl_snapshot_hash,
            "chain_hash": self.chain_hash,
            "deterministic_id": self.deterministic_id,
        }

# ---------------------------------------------------------------------------
# Helper – deterministic SHA‑256 of a string
# ---------------------------------------------------------------------------
def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

# ---------------------------------------------------------------------------
# Build a deterministic hash chain for a full run
# ---------------------------------------------------------------------------
def build_hash_chain(seed: int, num_ticks: int, mode: str = "autonomous") -> Tuple[HashChainEntry, ...]:
    """Run a simulation for *num_ticks* ticks and return a deterministic hash chain.
    Only the world_state_hash is filled; other component hashes are empty strings.
    """
    prior_chain_hash = _sha256("scrubin_genesis")
    entries: List[HashChainEntry] = []
    orch = Orchestrator(seed=seed, mode=mode)
    orch.setup()
    for _ in range(num_ticks):
        orch.tick()
        ws_hash = world_hash(orch.world)
        payload = {
            "tick": orch.tick_count,
            "world_state_hash": ws_hash,
            "physiology_hash": "",
            "cognition_hash": "",
            "resource_hash": "",
            "agent_hash": "",
            "rl_snapshot_hash": "",
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        chain_hash = _sha256(prior_chain_hash + canonical)
        deterministic_id = _sha256(f"{orch.tick_count}:{chain_hash}")
        entry = HashChainEntry(
            tick=orch.tick_count,
            world_state_hash=ws_hash,
            physiology_hash="",
            cognition_hash="",
            resource_hash="",
            agent_hash="",
            rl_snapshot_hash="",
            chain_hash=chain_hash,
            deterministic_id=deterministic_id,
        )
        entries.append(entry)
        prior_chain_hash = chain_hash
    return tuple(entries)

# ---------------------------------------------------------------------------
# Validation – ensure chain continuity and deterministic IDs
# ---------------------------------------------------------------------------
def validate_chain(chain: Tuple[HashChainEntry, ...]) -> bool:
    if not chain:
        return False
    prior = _sha256("scrubin_genesis")
    for entry in chain:
        payload = {
            "tick": entry.tick,
            "world_state_hash": entry.world_state_hash,
            "physiology_hash": entry.physiology_hash,
            "cognition_hash": entry.cognition_hash,
            "resource_hash": entry.resource_hash,
            "agent_hash": entry.agent_hash,
            "rl_snapshot_hash": entry.rl_snapshot_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected_chain_hash = _sha256(prior + canonical)
        if expected_chain_hash != entry.chain_hash:
            return False
        expected_det_id = _sha256(f"{entry.tick}:{entry.chain_hash}")
        if expected_det_id != entry.deterministic_id:
            return False
        prior = entry.chain_hash
    return True
