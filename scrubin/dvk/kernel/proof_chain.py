from typing import List, Optional
from scrubin.dvk.kernel.proof_object import ExecutionProofObject

class ProofChain:
    """
    Append-only linked chain of Execution Proof Objects.
    Each EPO references the hash of its predecessor, forming a tamper-evident log.
    """
    def __init__(self):
        self._chain: List[ExecutionProofObject] = []

    def append(self, epo: ExecutionProofObject):
        if self._chain:
            assert epo.previous_proof_hash == self._chain[-1].current_proof_hash, \
                "Chain integrity violation: previous_proof_hash does not match."
        self._chain.append(epo)

    def latest(self) -> Optional[ExecutionProofObject]:
        return self._chain[-1] if self._chain else None

    def verify_chain(self) -> bool:
        for i in range(1, len(self._chain)):
            if self._chain[i].previous_proof_hash != self._chain[i-1].current_proof_hash:
                return False
        return True

    def __len__(self):
        return len(self._chain)
