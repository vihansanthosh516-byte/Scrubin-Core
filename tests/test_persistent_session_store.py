import os
import shutil
import hashlib
import tempfile

from scrubin.api.persistent_session_store import PersistentSessionStore, SessionMetadata
from scrubin.api.serialization import serialize_worldstate
from scrubin.world.state import WorldState


def _hash_state(state: WorldState) -> str:
    payload = serialize_worldstate(state)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def test_create_save_load_delete_and_hash():
    # Use a temporary directory for storage to avoid polluting repo
    tmp_dir = tempfile.mkdtemp(prefix='session_store_test_')
    try:
        store = PersistentSessionStore(storage_dir=tmp_dir)
        # Initial world state
        initial = WorldState(tick=0, seed=123)
        # Create session
        meta = store.create_session('sess1', initial)
        assert meta.session_id == 'sess1'
        assert meta.created_at_tick == initial.tick
        assert meta.last_saved_tick == initial.tick
        assert meta.simulation_seed == initial.seed
        assert meta.world_hash == _hash_state(initial)
        assert meta.schema_version == 1
        # List sessions
        assert store.list_sessions() == ['sess1']
        # Save after progress
        progressed = WorldState(tick=5, seed=123)
        meta2 = store.save_session('sess1', progressed)
        assert meta2.last_saved_tick == progressed.tick
        assert meta2.created_at_tick == initial.tick
        assert meta2.world_hash == _hash_state(progressed)
        # Load and verify
        loaded_state, loaded_meta = store.load_session('sess1')
        assert loaded_state == progressed
        assert loaded_meta == meta2
        # Replay guarantee: continue without saving should match after load
        continued = WorldState(tick=6, seed=123)
        # Save the continued state
        meta3 = store.save_session('sess1', continued)
        # Load again
        loaded_state2, loaded_meta2 = store.load_session('sess1')
        assert loaded_state2 == continued
        assert loaded_meta2.last_saved_tick == continued.tick
        # Create a second session
        second = WorldState(tick=0, seed=999)
        meta_sec = store.create_session('sess2', second)
        assert set(store.list_sessions()) == {'sess1', 'sess2'}
        # Delete first session
        store.delete_session('sess1')
        assert store.list_sessions() == ['sess2']
        # Deleting nonexistent session raises
        try:
            store.delete_session('nonexistent')
            assert False, 'Expected FileNotFoundError'
        except FileNotFoundError:
            pass
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
