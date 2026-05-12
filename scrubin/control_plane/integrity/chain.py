import hashlib
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time

@dataclass
class IntegrityBlock:
    index: int
    timestamp: float
    job_id: str
    data: Dict[str, Any]
    previous_hash: str
    hash: str

class ExecutionAuditChain:
    """
    Cryptographic audit trail for job execution and state transitions.
    """
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.chain: List[IntegrityBlock] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_data = {"event": "GENESIS", "job_id": self.job_id}
        self.add_block(genesis_data, "0")

    def add_block(self, data: Dict[str, Any], prev_hash: Optional[str] = None) -> str:
        index = len(self.chain)
        timestamp = time.time()
        p_hash = prev_hash or (self.chain[-1].hash if self.chain else "0")
        
        block_content = f"{index}{timestamp}{self.job_id}{json.dumps(data, sort_keys=True)}{p_hash}"
        current_hash = hashlib.sha256(block_content.encode()).hexdigest()
        
        block = IntegrityBlock(index, timestamp, self.job_id, data, p_hash, current_hash)
        self.chain.append(block)
        return current_hash

    def validate_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Re-calculate hash
            block_content = f"{current.index}{current.timestamp}{current.job_id}{json.dumps(current.data, sort_keys=True)}{current.previous_hash}"
            if current.hash != hashlib.sha256(block_content.encode()).hexdigest():
                return False
            
            if current.previous_hash != previous.hash:
                return False
        return True

    def get_certification(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "blocks": len(self.chain),
            "head_hash": self.chain[-1].hash if self.chain else "0",
            "verified": self.validate_chain(),
            "certification_status": "CERTIFIED_REPRODUCIBLE" if self.validate_chain() else "TAMPERED"
        }
