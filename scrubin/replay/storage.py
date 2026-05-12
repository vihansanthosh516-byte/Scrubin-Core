import pickle
import zlib

from scrubin.world.model import SimulationWorld
from scrubin.world.hospital import HospitalWorld


class SnapshotStorage:
    @staticmethod
    def compress(world: SimulationWorld | HospitalWorld) -> bytes:
        serialized = pickle.dumps(world, protocol=pickle.HIGHEST_PROTOCOL)
        return zlib.compress(serialized)

    @staticmethod
    def decompress(data: bytes) -> SimulationWorld | HospitalWorld:
        serialized = zlib.decompress(data)
        return pickle.loads(serialized)
