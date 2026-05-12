from typing import Any
from scrubin.control_plane.kernel import ControlPlaneKernel

class CoreBinding:
    """
    Standardizes the connection between Control Plane and ScrubIn Core.
    """
    def __init__(self, orchestrator: Any):
        # The orchestrator is the existing core entry point
        self.orchestrator = orchestrator
        self.control_plane = ControlPlaneKernel(self.orchestrator)

    def dispatch(self):
        """
        Main execution loop for the control plane.
        """
        return self.control_plane.execute_next_job()

    def get_api(self):
        from scrubin.control_plane.api import ControlPlaneAPI
        return ControlPlaneAPI(self.control_plane)
