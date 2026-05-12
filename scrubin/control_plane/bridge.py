from typing import Dict, Any, Optional
from scrubin.control_plane.jobs import Job, JobType
from scrubin.control_plane.sessions import SessionConfig

class ControlPlaneBridge:
    """
    Translates orchestration commands into simulation core triggers.
    STRICT RULE: No simulation or clinical logic allowed here.
    """
    def __init__(self, simulation_kernel: Any):
        self.kernel = simulation_kernel

    def execute_job_trigger(self, job: Job):
        """
        Routes job execution to the appropriate core engine.
        """
        if job.type == JobType.HIERARCHICAL_SIMULATION:
            self._trigger_hierarchical(job)
        elif job.type == JobType.MULTI_AGENT_SIMULATION:
            self._trigger_multi_agent(job)
        elif job.type == JobType.VECTOR_BATCH_SIMULATION:
            self._trigger_vector_batch(job)
        elif job.type == JobType.ONLINE_LEARNING:
            self._trigger_learning(job)

    def configure_session(self, config: SessionConfig):
        """
        Translates control plane config into session setup.
        """
        # This is where experiment.policy_overrides would be injected
        # into the simulation core via the kernel.
        pass

    def _trigger_hierarchical(self, job: Job):
        # Dispatches to scrubin/decision/hierarchical/
        pass

    def _trigger_multi_agent(self, job: Job):
        # Dispatches to scrubin/agents/teams/
        pass

    def _trigger_vector_batch(self, job: Job):
        # Dispatches to scrubin/runtime/vectorized/
        pass

    def _trigger_learning(self, job: Job):
        # Dispatches to scrubin/learning/
        pass
