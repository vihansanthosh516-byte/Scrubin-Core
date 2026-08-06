import zlib
import json
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


def _episode_to_jsonable(trajectory: List[dict]) -> Any:
    """Coerce an episode trajectory into a JSON-serialisable structure.

    Individual episode records are expected to be plain dicts; any nested
    objects exposing ``to_dict`` are converted automatically, and anything
    else is stringified to keep the payload JSON-safe (and un-pickleable).
    """
    def _coerce(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): _coerce(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_coerce(v) for v in value]
        if hasattr(value, "to_dict"):
            return _coerce(value.to_dict())
        return str(value)

    return [_coerce(item) for item in trajectory]


class EpisodicMemory:
    """
    Deduplicates and stores important clinical episodes.

    Episodes are serialised as JSON (via :meth:`json.dumps`) rather than pickle,
    so stored blobs cannot trigger arbitrary code execution on retrieval.
    """
    def __init__(self):
        self.episodes: Dict[str, bytes] = {}

    def store(self, episode_id: str, trajectory: List[dict]):
        payload = _episode_to_jsonable(trajectory)
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.episodes[episode_id] = zlib.compress(data)

    def retrieve(self, episode_id: str) -> List[dict]:
        if episode_id not in self.episodes:
            return []
        data = zlib.decompress(self.episodes[episode_id])
        return json.loads(data.decode("utf-8"))
