import time
from typing import List, Dict, Any, Optional
from scrubin.control_plane.streaming.event_stream import EventStream, StreamEvent

class LiveReplayEngine:
    """
    Provides playback controls for simulation event streams.
    """
    def __init__(self, stream: EventStream):
        self.stream = stream
        self.current_tick = 0
        self.playback_speed = 1.0
        self._is_paused = False

    def play_from(self, start_tick: int = 0):
        self.current_tick = start_tick
        self._is_paused = False
        print(f"[REPLAY] Starting playback from tick {start_tick} at {self.playback_speed}x")

    def pause(self):
        self._is_paused = True
        print(f"[REPLAY] Playback paused at tick {self.current_tick}")

    def step(self) -> Optional[List[StreamEvent]]:
        if self._is_paused:
            return None
            
        events = self.stream.replay(since_tick=self.current_tick)
        tick_events = [e for e in events if e.tick == self.current_tick]
        
        self.current_tick += 1
        return tick_events

    def seek(self, tick: int):
        self.current_tick = tick
        print(f"[REPLAY] Seek to tick {tick}")
