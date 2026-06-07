import hashlib, shutil, tempfile

from scrubin.world.state import WorldState
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.engine.random import SimulationRNG
from scrubin.api.persistent_session_store import PersistentSessionStore
from scrubin.api.serialization import serialize_worldstate


def _hash_state(state):
    payload = serialize_worldstate(state)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def test_persistence_replay_continuation():
    storage_dir = tempfile.mkdtemp(prefix='p2_test_')
    try:
        seed = 42
        # ---------- Branch A – continuous execution ----------
        rng_a = SimulationRNG(seed)
        engine_a = PhysiologicEvolutionEngine(rng_a)
        world_a = WorldState(tick=0, seed=seed)
        for _ in range(40):
            world_a = engine_a.evolve(world_a)

        # ---------- Branch B – save / load / continue ----------
        rng_b = SimulationRNG(seed)
        engine_b = PhysiologicEvolutionEngine(rng_b)
        world_b = WorldState(tick=0, seed=seed)
        for _ in range(20):
            world_b = engine_b.evolve(world_b)
        store = PersistentSessionStore(storage_dir=storage_dir)
        store.create_session('test_session', world_b)
        loaded_world, meta = store.load_session('test_session')
        assert loaded_world == world_b
        assert meta.world_hash == _hash_state(world_b)
        for _ in range(20):
            loaded_world = engine_b.evolve(loaded_world)
        assert loaded_world == world_a
        assert loaded_world.tick == world_a.tick
        assert _hash_state(loaded_world) == _hash_state(world_a)
    finally:
        shutil.rmtree(storage_dir, ignore_errors=True)
