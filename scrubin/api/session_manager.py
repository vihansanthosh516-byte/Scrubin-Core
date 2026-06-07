"""Session manager for Scrubin backend API.

The manager owns a private in‑memory mapping ``session_id -> WorldState``.
All operations are pure: a new immutable ``WorldState`` is produced and the
stored mapping is updated atomically.  No mutable state is exposed to the
frontend – the only mutable component is the internal dictionary which is an
implementation detail of the backend.
"""

from __future__ import annotations

import uuid
from typing import Dict

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent

from .api_contracts import (
    SimulationCreateRequest,
    SimulationCreateResponse,
    SimulationActionRequest,
    SimulationActionResponse,
    SimulationStateResponse,
)


class SessionManager:
    """In‑memory session manager.

    Each session holds exactly one immutable ``WorldState``.  The manager
    provides methods to create a session, apply a deterministic action, and
    query the current state.
    """

    def __init__(self) -> None:
        # Mapping from session_id (hex string) to the current WorldState.
        self._sessions: Dict[str, WorldState] = {}

    # ---------------------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------------------
    def create_session(self, request: SimulationCreateRequest) -> SimulationCreateResponse:
        """Create a new session and return the initial world.

        The ``seed`` is passed directly to ``WorldState``; the ``initial_tick``
        is used as the starting tick.  No other engine is invoked – the
        session starts with a clean deterministic world.
        """
        session_id = uuid.uuid4().hex
        world = WorldState(tick=request.initial_tick, seed=request.seed)
        self._sessions[session_id] = world
        return SimulationCreateResponse(session_id=session_id, initial_world_state=world)

    # ---------------------------------------------------------------------
    # Action handling (placeholder deterministic behaviour)
    # ---------------------------------------------------------------------
    def apply_action(self, request: SimulationActionRequest) -> SimulationActionResponse:
        """Apply a deterministic placeholder action to the session.

        For the purpose of the API foundation we do **not** invoke the full
        cognition pipeline.  Instead we perform a minimal deterministic update:
        * Append a ``TimelineEvent`` describing the requested action.
        * Advance the simulation tick by one.
        The result mimics a real engine step while keeping the implementation
        simple and deterministic.
        """
        if request.session_id not in self._sessions:
            raise KeyError(f"Session '{request.session_id}' not found")

        # Retrieve current world (immutable).
        world = self._sessions[request.session_id]

        # Create a deterministic event for the action.
        event = TimelineEvent(tick=world.tick, description=f"action_performed:{request.action_type}")
        # Apply the event and advance the tick.
        new_world = world.append_timeline(event).tick_forward()

        # Store the updated world.
        self._sessions[request.session_id] = new_world

        # Build deterministic response payloads.
        return SimulationActionResponse(
            world_tick=new_world.tick,
            timeline_events=(event,),
            updated_score=0.0,  # placeholder – scoring is domain specific.
            updated_world_state=new_world,
            active_goals=new_world.goal_hierarchy_state.active_goals,
            active_intents=new_world.intentive_cognition_state.active_intents,
            reflection_summary=new_world.reflection_state,
            learning_summary=new_world.learning_state,
        )

    # ---------------------------------------------------------------------
    # State query
    # ---------------------------------------------------------------------
    def get_state(self, session_id: str) -> SimulationStateResponse:
        """Return the current immutable snapshot for a session.

        The returned ``SimulationStateResponse`` contains the full ``WorldState``
        as well as convenient aggregates for the client.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found")
        world = self._sessions[session_id]
        return SimulationStateResponse(
            world_tick=world.tick,
            timeline_events=world.timeline,
            updated_score=0.0,
            current_world_state=world,
            active_goals=world.goal_hierarchy_state.active_goals,
            active_intents=world.intentive_cognition_state.active_intents,
            reflection_summary=world.reflection_state,
            learning_summary=world.learning_state,
        )
