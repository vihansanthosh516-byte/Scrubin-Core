import uuid
from typing import Any, Dict

from .execution_context import ExecutionContext
from .isolation_engine import IsolationEngine


class RunManager:
    """P8 orchestration layer handling multiple independent runs.

    Parameters
    ----------
    engine: IsolationEngine
        Engine that performs the isolated execution.
    """

    def __init__(self, engine: IsolationEngine):
        self.engine = engine

    def submit(self, config: Dict[str, Any]):
        """Create a new run and execute it.

        ``config`` may contain ``seed``, ``ticks``, and ``initial_state`` entries.
        Returns the ``ExecutionArtifact`` produced by the engine.
        """
        run_id = str(uuid.uuid4())

        context = ExecutionContext(
            run_id=run_id,
            seed=config.get("seed", 42),
            config=config,
            initial_state=config.get("initial_state", {}),
        )

        return self.engine.run(context)

    def get(self, run_id: str):
        """Retrieve a stored ``ExecutionArtifact`` by its ``run_id``.
        Returns ``None`` if the run is unknown.
        """
        return self.engine.store.get(run_id)
