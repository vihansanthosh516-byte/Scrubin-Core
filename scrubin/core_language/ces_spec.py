from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

class CESScope(Enum):
    PATIENT = "patient"
    HOSPITAL = "hospital"
    POPULATION = "population"

@dataclass
class CESCondition:
    """Causal trigger condition for a CES instruction."""
    trigger: str          # e.g. "spo2 < 88 AND respiratory_failure"
    scope: CESScope = CESScope.PATIENT

@dataclass
class CESAction:
    """Atomic intervention payload."""
    action: str           # e.g. "ADMINISTER_OXYGEN"
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CESConstraints:
    """Phase 13-15 safety + physiology + resource bounds."""
    physiology: str = ""
    safety: str = ""
    resource: str = ""

@dataclass
class CESCausalAnchor:
    """Links this instruction to its causal justification."""
    ceg_node: str = ""
    counterfactual_origin: str = ""

@dataclass
class CESObjective:
    """Phase 15.1 reward + penalty binding."""
    reward: float = 0.0
    penalty_model: str = "Phase15.1"

@dataclass
class CESInstruction:
    """
    The atomic unit of the Causal Execution Language.
    Every action in ScrubIn — RL, policy, global, counterfactual — compiles to this.
    """
    id: str
    scope: CESScope

    when: CESCondition
    do: CESAction
    constraints: CESConstraints = field(default_factory=CESConstraints)
    causal_anchor: CESCausalAnchor = field(default_factory=CESCausalAnchor)
    objective: CESObjective = field(default_factory=CESObjective)

@dataclass
class CESProgram:
    """Ordered collection of CES instructions forming a complete executable program."""
    program_id: str
    instructions: List[CESInstruction] = field(default_factory=list)
    seed: int = 0

    def add(self, instruction: CESInstruction):
        self.instructions.append(instruction)
