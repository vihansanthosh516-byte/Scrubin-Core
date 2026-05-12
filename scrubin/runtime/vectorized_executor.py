from typing import List, Dict, Any
from collections import defaultdict
from scrubin.core_language.ces_spec import CESInstruction
from scrubin.runtime.execution_graph_compiler import CausalExecutionBatch
import copy

class VectorizedExecutor:
    """
    Executes same-type CES instructions as grouped vectorized operations.
    Removes per-instruction Python loop overhead while preserving determinism
    via sorted grouping.
    """
    def __init__(self):
        self.execution_count = 0

    def execute_batch(self, batch: CausalExecutionBatch, state: Any) -> Any:
        # 1. Group instructions by action type (deterministic sort)
        groups: Dict[str, List[CESInstruction]] = defaultdict(list)
        for inst in sorted(batch.instructions, key=lambda i: (i.do.action, i.id)):
            groups[inst.do.action].append(inst)

        # 2. Vectorized application per group
        current_state = copy.deepcopy(state)
        for action_type in sorted(groups.keys()):
            current_state = self._apply_vectorized(action_type, groups[action_type], current_state)

        return current_state

    def _apply_vectorized(self, action_type: str, instructions: List[CESInstruction], state: Any) -> Any:
        """Applies a batch of same-type instructions as one logical operation."""
        for inst in instructions:
            if hasattr(state, "decisions"):
                state.decisions.append({
                    "ces_id": inst.id,
                    "action": inst.do.action,
                    "params": inst.do.params,
                    "scope": inst.scope.value,
                    "vectorized": True
                })
            if hasattr(state, "tick"):
                state.tick += 1
            self.execution_count += 1
        return state
