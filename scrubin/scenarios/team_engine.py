'''Deterministic OR team engine – handles role assignments, instrument state, and communication events.'''

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Tuple, List, Dict

# Import static role definitions and Step model
from .models import TeamRole, Step

# ---------------------------------------------------------------------------
# Dynamic role state during execution
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TeamMember:
    '''Dynamic state for a team member during scenario execution.'''
    id: str
    role_type: str
    current_task: str = ''
    workload: int = 0
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic identifier derived from static fields only.
        object.__setattr__(self, 'deterministic_id', hashlib.sha256(self.id.encode()).hexdigest())

# ---------------------------------------------------------------------------
# Instrument state – immutable per instrument.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class InstrumentState:
    '''Immutable state of a surgical instrument.'''
    id: str
    status: str = 'available'
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Hash includes identifier and status for deterministic replay.
        object.__setattr__(self, 'deterministic_id', hashlib.sha256(f'{self.id}:{self.status}'.encode()).hexdigest())

# ---------------------------------------------------------------------------
# Overall team snapshot – immutable.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TeamState:
    members: Tuple[TeamMember, ...] = field(default_factory=tuple)
    instruments: Tuple[InstrumentState, ...] = field(default_factory=tuple)
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        member_part = '|'.join(sorted(f'{m.id}:{m.workload}' for m in self.members))
        instr_part = '|'.join(sorted(f'{i.id}:{i.status}' for i in self.instruments))
        combined = f'{member_part}|{instr_part}'
        object.__setattr__(self, 'deterministic_id', hashlib.sha256(combined.encode()).hexdigest())

# ---------------------------------------------------------------------------
# Team task engine – assigns work, updates instrument status, emits events.
# ---------------------------------------------------------------------------

class TeamTaskEngine:
    '''Deterministic engine for assigning workflow steps to team members.'''

    def __init__(self, roles: Tuple[TeamRole, ...], instrument_ids: Tuple[str, ...]):
        # Convert static role definitions into mutable members for execution state.
        self.initial_members = tuple(TeamMember(id=r.id, role_type=r.role_type) for r in roles)
        self.instrument_ids = instrument_ids

    def initial_state(self) -> TeamState:
        instruments = tuple(InstrumentState(id=i) for i in self.instrument_ids)
        return TeamState(members=self.initial_members, instruments=instruments)

    def process_step(self, step: Step, state: TeamState) -> Tuple[TeamState, List[Dict]]:
        '''Assign step to required roles, manage instruments, emit deterministic events.'''
        events: List[Dict] = []
        # -------------------------------------------------------------
        # Role assignment – honor required_roles on the step (if any).
        # -------------------------------------------------------------
        required_roles = getattr(step, 'required_roles', ())
        assigned: Dict[str, TeamMember] = {}
        for role_type in required_roles:
            candidate = None
            for m in sorted(state.members, key=lambda x: x.id):
                if m.role_type == role_type and m.current_task == '':
                    candidate = m
                    break
            if candidate is None:
                events.append({'type': 'TaskFailed', 'step': step.id, 'reason': f'{role_type}_unavailable'})
                return state, events
            assigned[role_type] = candidate
        # -------------------------------------------------------------
        # Instrument handling – each required instrument must be available.
        # -------------------------------------------------------------
        new_members = list(state.members)
        new_instruments = list(state.instruments)
        primary_role_id = None
        if required_roles:
            primary_role_id = assigned[required_roles[0]].id
        for instr_id in sorted(step.required_instruments):
            instr = next((i for i in new_instruments if i.id == instr_id), None)
            if instr is None:
                events.append({'type': 'TaskFailed', 'step': step.id, 'reason': 'instrument_missing'})
                return state, events
            if instr.status != 'available':
                events.append({'type': 'TaskFailed', 'step': step.id, 'reason': 'instrument_unavailable'})
                return state, events
            if primary_role_id:
                events.append({'type': 'InstrumentRequested', 'by_role': primary_role_id, 'instrument': instr_id})
                events.append({'type': 'InstrumentAcknowledged', 'by_role': primary_role_id, 'instrument': instr_id})
            # Mark instrument as in_use (transient) then back to available.
            instr = replace(instr, status='in_use')
            events.append({'type': 'InstrumentInUse', 'instrument': instr_id, 'by_role': primary_role_id})
            instr = replace(instr, status='available')
            idx = new_instruments.index(next(i for i in new_instruments if i.id == instr_id))
            new_instruments[idx] = instr
        # -------------------------------------------------------------
        # Update member workload and emit task events.
        # -------------------------------------------------------------
        for role_type, member in assigned.items():
            idx = new_members.index(member)
            updated = replace(member, workload=member.workload + 1, current_task=step.id)
            events.append({'type': 'TaskAssigned', 'role': member.id, 'task': step.id})
            events.append({'type': 'TaskCompleted', 'role': member.id, 'task': step.id})
            updated = replace(updated, current_task='')
            new_members[idx] = updated
        new_state = replace(state, members=tuple(new_members), instruments=tuple(new_instruments))
        return new_state, events
