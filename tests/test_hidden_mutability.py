"""Hidden mutability detection test.

Ensures that all dataclasses across the core packages are frozen and that no
mutable objects are used as default values (which would break replay safety).
"""

import importlib
import pkgutil
import inspect
from dataclasses import is_dataclass, fields, MISSING

# List of top‑level packages to scan for dataclasses.
_PACKAGES = [
    "scrubin.ontology",
    "scrubin.execution",
    "scrubin.biology",
    "scrubin.adaptive",
    "scrubin.environment",
    "scrubin.memory",
    "scrubin.recovery",
    "scrubin.agents",
    "scrubin.cognition",
]


def _iter_dataclasses():
    for pkg_name in _PACKAGES:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            continue
        if not hasattr(pkg, "__path__"):
            continue
        for _, mod_name, is_pkg in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
            if is_pkg:
                continue
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if is_dataclass(obj):
                    yield obj


def test_dataclasses_are_frozen_and_have_no_mutable_defaults():
    for cls in _iter_dataclasses():
        # Verify the dataclass is frozen.
        params = getattr(cls, "__dataclass_params__", None)
        assert params is not None and params.frozen, f"Dataclass {cls.__module__}.{cls.__name__} is not frozen"
        # Verify fields do not use mutable default values without a factory.
        for f in fields(cls):
            if f.default is not MISSING and isinstance(f.default, (list, dict, set)):
                raise AssertionError(
                    f"Mutable default for field '{f.name}' in dataclass {cls.__module__}.{cls.__name__}: {f.default}"
                )
