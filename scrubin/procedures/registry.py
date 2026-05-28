"""Procedure registry – loads structured surgical procedure definitions.

Procedures are stored as individual ``.json`` files in this package directory.
Each file name (without extension) is the procedure ID.
"""

import json
from pathlib import Path
from typing import Dict, Any

# Directory containing the JSON files – same directory as this module.
BASE_DIR = Path(__file__).parent


def _procedure_path(proc_id: str) -> Path:
    """Return the absolute path for a procedure JSON file.

    Args:
        proc_id: Procedure identifier (filename without .json).
    """
    return BASE_DIR / f"{proc_id}.json"


def get_procedure(proc_id: str) -> Dict[str, Any]:
    """Load and return a procedure definition.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
    """
    path = _procedure_path(proc_id)
    if not path.is_file():
        raise FileNotFoundError(f"Procedure {proc_id!r} not found")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def list_procedures() -> Dict[str, Dict[str, Any]]:
    """Return a mapping of procedure_id → definition for all JSON files.

    The function reads each file lazily; for a small catalog this is fine.
    """
    procedures: Dict[str, Dict[str, Any]] = {}
    for file in BASE_DIR.glob("*.json"):
        proc_id = file.stem
        procedures[proc_id] = get_procedure(proc_id)
    return procedures
