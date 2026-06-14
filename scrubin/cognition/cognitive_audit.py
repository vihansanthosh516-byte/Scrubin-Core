"""Static audit utilities for the deterministic cognition stack.

The audit scans source files for patterns that violate the deterministic
append‑only, immutable design (e.g., destructive mutators like ``del``,
``pop(``, ``remove(``, or filesystem deletions).  It returns a list of warning
messages; callers can decide whether to treat them as errors.
"""

from __future__ import annotations

import re
import os
from pathlib import Path
from typing import List

# Simple regex matching common destructive operations.
_PROHIBITED_PATTERN = re.compile(r"\b(del|pop\(|remove\(|os\.remove|os\.rmdir|shutil\.rmtree)\b")


def _find_python_files(root: Path) -> List[Path]:
    """Recursively collect ``.py`` files under *root* (excluding virtual‑envs)."""
    return [p for p in root.rglob("*.py") if "site-packages" not in str(p) and "venv" not in str(p)]


def run_cognitive_audit(root_dir: str = ".") -> List[str]:
    """Scan the codebase for prohibited mutable patterns.

    Parameters
    ----------
    root_dir: str, optional
        Directory to start the recursive search from. Defaults to the project
        root (``"."``) which works when the package is imported from the repo
        root.

    Returns
    -------
    List[str]
        Human‑readable warning messages for each offending line. An empty list means
        no prohibited patterns were found.
    """
    warnings: List[str] = []
    root_path = Path(root_dir).resolve()
    for file_path in _find_python_files(root_path):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if _PROHIBITED_PATTERN.search(line):
                warnings.append(
                    f"{file_path}:{i}: prohibited mutable operation -> {line.strip()}"
                )
    return warnings
