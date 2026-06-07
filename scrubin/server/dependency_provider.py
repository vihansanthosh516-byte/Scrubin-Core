from __future__ import annotations

from scrubin.api.session_manager import SessionManager
from scrubin.api.persistent_session_store import PersistentSessionStore
from scrubin.control_plane.kernel import ControlPlaneKernel

# Singleton instances – deterministic, reused across requests.
_SESSION_MANAGER = SessionManager()
_PERSISTENT_STORE = PersistentSessionStore()
_KERNEL = ControlPlaneKernel(core_interface=None)

# Experiment manager – deterministic experiment orchestration.
from scrubin.experiments.experiment_manager import ExperimentManager
_EXPERIMENT_MANAGER = ExperimentManager(_KERNEL)

# Planner engine – deterministic experiment planning (Phase P.12).
from scrubin.planner.experiment_planner import ExperimentPlanner
_PLANNER_ENGINE = ExperimentPlanner(_KERNEL)

# Adaptive search engine – deterministic adaptive experiment recommendation (Phase P.13).
from scrubin.search.adaptive_search import AdaptiveSearchEngine
_ADAPTIVE_SEARCH_ENGINE = AdaptiveSearchEngine()

# Optimization manager – deterministic multi‑objective analysis (Phase P.14).
from scrubin.optimization.optimization_manager import OptimizationManager
_OPTIMIZATION_MANAGER = OptimizationManager()

def get_session_manager() -> SessionManager:
    """FastAPI dependency returning the shared SessionManager instance."""
    return _SESSION_MANAGER

def get_persistent_store() -> PersistentSessionStore:
    """FastAPI dependency returning the shared PersistentSessionStore instance."""
    return _PERSISTENT_STORE

def get_kernel() -> ControlPlaneKernel:
    """FastAPI dependency returning the shared ControlPlaneKernel instance."""
    return _KERNEL

def get_experiment_manager() -> ExperimentManager:
    """FastAPI dependency returning the shared ExperimentManager instance."""
    return _EXPERIMENT_MANAGER

def get_planner_engine() -> ExperimentPlanner:
    """FastAPI dependency returning the shared ExperimentPlanner instance."""
    return _PLANNER_ENGINE


def get_adaptive_search_engine() -> AdaptiveSearchEngine:
    """FastAPI dependency returning the shared AdaptiveSearchEngine instance."""
    return _ADAPTIVE_SEARCH_ENGINE

def get_optimization_manager() -> OptimizationManager:
    """FastAPI dependency returning the shared OptimizationManager instance."""
    return _OPTIMIZATION_MANAGER
