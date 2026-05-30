from __future__ import annotations

"""Deterministic episodic memory compression utilities.

The engine aggregates repetitive decision chains into compressed ``Episode``
records.  For the current deterministic stub a single dummy episode is appended on
each call to ``compress``.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple, Any


@dataclass(frozen=True)
class CompressedEpisode:
    episode_id: str
    semantic_tags: Tuple[str, ...] = field(default_factory=tuple)
    dominant_failure_pattern: str = ""
    dominant_success_pattern: str = ""
    duration: int = 0
    cumulative_instability: float = 0.0
    cognitive_signature: Tuple[Any, ...] = field(default_factory=tuple)
    strategic_signature: Tuple[Any, ...] = field(default_factory=tuple)
    recovery_quality: float = 0.0
    complication_chain: Tuple[Any, ...] = field(default_factory=tuple)

    def with_duration(self, duration: int) -> "CompressedEpisode":
        return replace(self, duration=duration)


@dataclass(frozen=True)
class EpisodicMemory:
    episodes: Tuple[CompressedEpisode, ...] = field(default_factory=tuple)

    def add_episode(self, episode: CompressedEpisode) -> "EpisodicMemory":
        return replace(self, episodes=self.episodes + (episode,))


class MemoryCompressionEngine:
    """Compress procedural memory into deterministic episodic records.

    The placeholder implementation adds a single episode per tick with a
    deterministic identifier based on the current world tick.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def compress(self, world) -> Any:
        # Generate a deterministic episode identifier using the world tick.
        ep = CompressedEpisode(
            episode_id=f"ep_{world.tick}",
        )
        episodic_memory: EpisodicMemory = getattr(world, "episodic_memory", EpisodicMemory())
        episodic_memory = episodic_memory.add_episode(ep)
        return world.with_episodic_memory(episodic_memory)
