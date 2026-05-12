import zlib
import json
import pickle
from typing import List, Any, Dict


class MemoryCompressor:
    """
    Handles state compression and latent summaries for long-horizon hospital scaling.
    """
    @staticmethod
    def compress_state(state_dict: dict) -> bytes:
        """
        Compresses a world state dictionary using zlib.
        """
        data = json.dumps(state_dict, sort_keys=True).encode('utf-8')
        return zlib.compress(data)

    @staticmethod
    def decompress_state(compressed: bytes) -> dict:
        """
        Decompresses a world state.
        """
        data = zlib.decompress(compressed)
        return json.loads(data.decode('utf-8'))


class LatentSummarizer:
    """
    Creates low-dimensional summaries of physiological trajectories.
    Useful for MCTS pruning and long-term memory.
    """
    @staticmethod
    def summarize_trajectory(vitals_history: List[Dict[str, float]]) -> Dict[str, float]:
        if not vitals_history:
            return {}
        
        summary = {}
        keys = vitals_history[0].keys()
        for key in keys:
            values = [h.get(key, 0.0) for h in vitals_history]
            summary[f"{key}_mean"] = sum(values) / len(values)
            summary[f"{key}_trend"] = values[-1] - values[0]
            summary[f"{key}_min"] = min(values)
            summary[f"{key}_max"] = max(values)
        
        return summary


class EpisodicMemory:
    """
    Deduplicates and stores important clinical episodes.
    """
    def __init__(self):
        self.episodes: Dict[str, bytes] = {}

    def store(self, episode_id: str, trajectory: List[dict]):
        data = pickle.dumps(trajectory)
        self.episodes[episode_id] = zlib.compress(data)

    def retrieve(self, episode_id: str) -> List[dict]:
        if episode_id not in self.episodes:
            return []
        data = zlib.decompress(self.episodes[episode_id])
        return pickle.loads(data)
