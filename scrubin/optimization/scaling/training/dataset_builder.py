from typing import List, Dict, Any

class DatasetBuilder:
    """
    Transforms raw deterministic episode traces into structured RL training datasets.
    """
    def build(self, episode_traces: List[List[Any]]) -> List[Dict[str, Any]]:
        dataset = []
        for trace in episode_traces:
            for step in trace:
                dataset.append({
                    "obs": step[0],
                    "action": step[1],
                    "reward": step[2]
                })
        return dataset
