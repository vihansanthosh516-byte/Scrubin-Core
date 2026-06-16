"""Deterministic agent architecture unit tests.

These tests verify that agents, the deterministic communication engine, and the
agent engine produce repeatable events and message ordering without any hidden
state or randomness.
"""

from scrubin.agents import (
    AttendingSurgeon,
    ResidentSurgeon,
    ScrubNurse,
    AgentEngine,
    DeterministicCommunicationEngine,
    Message,
)


def test_agent_tick_assign_and_message():
    # Initialise agents.
    attending = AttendingSurgeon(agent_id="att1")
    resident = ResidentSurgeon(agent_id="res1")
    nurse = ScrubNurse(agent_id="nurse1")

    engine = AgentEngine(agents=(attending, resident, nurse))
    agents_after, events, comm = engine.tick()

    # All agents should have been assigned a task.
    assigned = {e["type"] for e in events if e["type"] == "TaskAssigned"}
    assert assigned == {"TaskAssigned"}
    assert len([e for e in events if e["type"] == "TaskAssigned"]) == 3

    # Scrub nurse should have sent a deterministic instrument request message.
    msgs, _ = comm.propagate()
    assert len(msgs) == 1
    msg = msgs[0]
    assert isinstance(msg, Message)
    assert msg.sender_id == "nurse1"
    assert msg.receiver_id == "AttendingSurgeon"
    assert msg.msg_type == "InstrumentRequest"
    # Message deterministic ID should be reproducible.
    expected_id = Message(
        sender_id="nurse1",
        receiver_id="AttendingSurgeon",
        msg_type="InstrumentRequest",
        content="Requesting scalpel",
    ).deterministic_id
    assert msg.deterministic_id == expected_id

    # Run a second tick – tasks should now complete and no new messages emitted.
    # Feed the pending communication engine (now empty after propagation).
    engine2 = AgentEngine(agents=agents_after, comm_engine=comm)
    agents_after2, events2, comm2 = engine2.tick()
    completed = [e for e in events2 if e["type"] == "TaskCompleted"]
    assert len(completed) == 3
    # No new messages should be queued.
    msgs2, _ = comm2.propagate()
    assert len(msgs2) == 0

    # Replay determinism – repeated runs yield identical final states.
    # Re‑run from the original engine.
    replay_engine = AgentEngine(agents=(attending, resident, nurse))
    a1, ev1, com1 = replay_engine.tick()
    a2, ev2, com2 = AgentEngine(a1, com1).tick()
    assert a2 == agents_after2
    assert ev2 == events2
    assert com2 == comm2
