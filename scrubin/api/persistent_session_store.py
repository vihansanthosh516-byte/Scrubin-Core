from __future__ import annotations

import json, os, hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .serialization import serialize_worldstate, deserialize_worldstate
from scrubin.world.state import WorldState

SCHEMA_VERSION = 1

@dataclass(frozen=True, slots=True)
class SessionMetadata:
    session_id: str
    created_at_tick: int
    last_saved_tick: int
    simulation_seed: int
    version: int
    world_hash: str
    schema_version: int = field(default=SCHEMA_VERSION)

    @staticmethod
    def from_state(session_id: str, state: WorldState, *, version: int = 1) -> 'SessionMetadata':
        payload = serialize_worldstate(state)
        world_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        return SessionMetadata(session_id, state.tick, state.tick, state.seed, version, world_hash)

class PersistentSessionStore:
    def __init__(self, storage_dir: str | None = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(__file__), 'sessions')
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f'{session_id}.json')

    def _write_file(self, path: str, data: Dict) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, sort_keys=True, separators=(',', ':'))

    def _read_file(self, path: str) -> Dict:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_session(self, session_id: str, initial_state: WorldState) -> SessionMetadata:
        path = self._session_path(session_id)
        if os.path.exists(path):
            raise FileExistsError(f'Session {session_id!r} exists')
        meta = SessionMetadata.from_state(session_id, initial_state)
        payload = serialize_worldstate(initial_state)
        data = {'metadata': {'session_id': meta.session_id,'created_at_tick': meta.created_at_tick,'last_saved_tick': meta.last_saved_tick,'simulation_seed': meta.simulation_seed,'version': meta.version,'world_hash': meta.world_hash,'schema_version': meta.schema_version},'world_state': payload}
        self._write_file(path, data)
        return meta

    def save_session(self, session_id: str, state: WorldState) -> SessionMetadata:
        path = self._session_path(session_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f'Session {session_id!r} not found')
        existing = self._read_file(path)['metadata']
        meta = SessionMetadata(session_id, existing.get('created_at_tick', state.tick), state.tick, state.seed, existing.get('version', 1), hashlib.sha256(serialize_worldstate(state).encode('utf-8')).hexdigest(), SCHEMA_VERSION)
        payload = serialize_worldstate(state)
        data = {'metadata': {'session_id': meta.session_id,'created_at_tick': meta.created_at_tick,'last_saved_tick': meta.last_saved_tick,'simulation_seed': meta.simulation_seed,'version': meta.version,'world_hash': meta.world_hash,'schema_version': meta.schema_version},'world_state': payload}
        self._write_file(path, data)
        return meta

    def load_session(self, session_id: str) -> Tuple[WorldState, SessionMetadata]:
        path = self._session_path(session_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f'Session {session_id!r} not found')
        data = self._read_file(path)
        meta_dict = data['metadata']
        meta = SessionMetadata(meta_dict['session_id'], meta_dict['created_at_tick'], meta_dict['last_saved_tick'], meta_dict['simulation_seed'], meta_dict['version'], meta_dict['world_hash'], meta_dict.get('schema_version', SCHEMA_VERSION))
        world = deserialize_worldstate(data['world_state'])
        return world, meta

    def delete_session(self, session_id: str) -> None:
        path = self._session_path(session_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f'Session {session_id!r} not found')
        os.remove(path)

    def list_sessions(self) -> List[str]:
        files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json')]
        return sorted([os.path.splitext(f)[0] for f in files])
