from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import time

class MessagePriority(Enum):
    ROUTINE = auto()
    URGENT = auto()
    STAT = auto()

class CommunicationChannel(Enum):
    VERBAL = auto()
    PAGER = auto()
    ELECTRONIC_NOTE = auto()
    HANDOFF = auto()

@dataclass
class Message:
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    content: str
    channel: CommunicationChannel
    priority: MessagePriority = MessagePriority.ROUTINE
    timestamp: float = field(default_factory=time.time)
    
    # Simulating failures
    is_delayed: bool = False
    is_garbled: bool = False
    is_lost: bool = False
    
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HandoffProtocol:
    patient_id: str
    situation: str
    background: str
    assessment: str
    recommendation: str  # SBAR format
    
    def to_message(self, sender: str, recipient: str) -> Message:
        content = f"S: {self.situation}\nB: {self.background}\nA: {self.assessment}\nR: {self.recommendation}"
        return Message(
            sender_id=sender,
            recipient_id=recipient,
            content=content,
            channel=CommunicationChannel.HANDOFF,
            priority=MessagePriority.URGENT
        )
