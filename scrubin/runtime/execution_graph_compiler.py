from typing import List, Dict, Set
from scrubin.core_language.ces_spec import CESInstruction, CESProgram

class CausalExecutionBatch:
    """A group of CES instructions with no cross-batch causal dependencies."""
    def __init__(self, batch_id: str, depth: int):
        self.batch_id = batch_id
        self.depth = depth
        self.instructions: List[CESInstruction] = []

    def add(self, inst: CESInstruction):
        self.instructions.append(inst)

class ExecutionGraphCompiler:
    """
    Converts a linear CES program into a DAG of Causal Execution Batches.
    Instructions at the same causal depth can execute in parallel.
    """
    def compile(self, program: CESProgram) -> List[CausalExecutionBatch]:
        # 1. Assign causal depth to each instruction
        #    Patient < Hospital < Population (scope ordering)
        depth_map = {"patient": 0, "hospital": 1, "population": 2}

        # 2. Group by causal depth
        batches_by_depth: Dict[int, CausalExecutionBatch] = {}
        for inst in program.instructions:
            d = depth_map.get(inst.scope.value, 0)
            if d not in batches_by_depth:
                batches_by_depth[d] = CausalExecutionBatch(
                    batch_id=f"batch_d{d}_{program.program_id}", depth=d
                )
            batches_by_depth[d].add(inst)

        # 3. Return in causal order (depth ascending)
        return [batches_by_depth[d] for d in sorted(batches_by_depth.keys())]
