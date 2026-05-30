from __future__ import annotations
"""Deterministic profiling helpers for the simulation runtime.

The functions provide lightweight, deterministic metrics without relying on
external profilers.  They are useful for unit‑tests that need to verify that
engine stages execute within reasonable bounds.
"""

import time
from typing import Callable, Dict, Any


def profile_engine(engine_name: str, func: Callable[[Any], Any], *args, **kwargs) -> Dict[str, Any]:
    """Measure the execution time of *func* and return a result dict.

    The return value contains the elapsed time in milliseconds and the
    function's return value under the ``"result"`` key.  This deterministic
    profiling can be used in tests to assert that an engine does not exceed a
    given budget.
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return {"engine": engine_name, "elapsed_ms": elapsed_ms, "result": result}


def dummy_profile() -> Dict[str, Any]:
    """Return a placeholder profile dict.

    Some tests may only need the presence of a profiling function; this stub
    supplies a deterministic, zero‑cost result.
    """
    return {"engine": "dummy", "elapsed_ms": 0.0, "result": None}
