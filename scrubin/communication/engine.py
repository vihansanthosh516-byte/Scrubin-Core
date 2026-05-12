import random
from typing import List, Dict, Optional
from scrubin.communication.models import Message, CommunicationChannel, MessagePriority

class CommunicationEngine:
    """
    Simulates the messy reality of clinical communication.
    """
    def __init__(self, failure_rate: float = 0.05):
        self.failure_rate = failure_rate
        self.message_queue: List[Message] = []
        self.delivered_messages: List[Message] = []

    def send_message(self, message: Message):
        # Determine if message is lost, delayed, or garbled
        roll = random.random()
        
        if roll < self.failure_rate:
            message.is_lost = True
            # We don't even queue it if it's lost
            return
        
        if roll < self.failure_rate * 2:
            message.is_delayed = True
            # Delayed messages will be delivered later
        
        if roll < self.failure_rate * 3:
            message.is_garbled = True
            message.content = self._garble_text(message.content)
            
        self.message_queue.append(message)

    def _garble_text(self, text: str) -> str:
        # Simple text garbling for simulation
        words = text.split()
        for i in range(len(words)):
            if random.random() < 0.2:
                words[i] = "..." if random.random() < 0.5 else "[unintelligible]"
        return " ".join(words)

    def process_tick(self):
        """
        Advance communication state.
        """
        still_queued = []
        for msg in self.message_queue:
            if msg.is_delayed:
                if random.random() < 0.3: # 30% chance to be delivered each tick
                    msg.is_delayed = False
                    self.delivered_messages.append(msg)
                else:
                    still_queued.append(msg)
            else:
                self.delivered_messages.append(msg)
        
        self.message_queue = still_queued

    def get_new_messages_for_agent(self, agent_id: str) -> List[Message]:
        received = [msg for msg in self.delivered_messages if msg.recipient_id == agent_id or msg.recipient_id is None]
        # Remove from delivered list once read? Or keep history?
        # Let's keep history but return only new ones if we track read status.
        return received
