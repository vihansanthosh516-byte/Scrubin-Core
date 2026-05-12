from typing import Any, List
from scrubin.core_language.ces_spec import CESProgram
from scrubin.runtime.execution_graph_compiler import ExecutionGraphCompiler
from scrubin.runtime.deterministic_scheduler import DeterministicScheduler
from scrubin.runtime.vectorized_executor import VectorizedExecutor

class CESBatchEngine:
    """
    High-performance CES execution pipeline.
    Compiles → Schedules → Vectorizes → Executes in causal batch order.
    """
    def __init__(self):
        self.graph_compiler = ExecutionGraphCompiler()
        self.scheduler = DeterministicScheduler()
        self.executor = VectorizedExecutor()

    def run(self, program: CESProgram, initial_state: Any) -> Any:
        # 1. Compile CES program into causal execution batches
        batches = self.graph_compiler.compile(program)

        # 2. Schedule batches in deterministic causal order
        ordered = self.scheduler.schedule(batches)

        # 3. Execute each batch via vectorized executor
        state = initial_state
        for batch in ordered:
            state = self.executor.execute_batch(batch, state)

        return state
