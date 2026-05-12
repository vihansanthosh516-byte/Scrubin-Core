from typing import List
from scrubin.runtime.execution_graph_compiler import CausalExecutionBatch

class DeterministicScheduler:
    """
    Causal priority scheduler for parallel CES execution.
    Guarantees that parallel execution produces the same result as sequential.
    """
    def schedule(self, batches: List[CausalExecutionBatch]) -> List[CausalExecutionBatch]:
        """
        Returns batches in strict causal order.
        Within each batch, instructions are pre-sorted by (action, id).
        """
        # 1. Sort batches by causal depth
        ordered = sorted(batches, key=lambda b: b.depth)

        # 2. Within each batch, sort instructions deterministically
        for batch in ordered:
            batch.instructions.sort(key=lambda i: (i.do.action, i.id))

        return ordered
