"""Procedure registry – loads structured surgical procedure definitions.

Procedures may be defined either as a single ``.json`` file **or** as a folder
containing multiple JSON parts (``config.json``, ``phases.json``, etc.).  When a
folder with the requested ``proc_id`` exists it is preferred over a single JSON
file.  The folder layout follows the Procedure SDK described in
``PROCEDURE_AUTHORING_GUIDELINES.md``.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

def _load_json(path: Path) -> Any:
    """Load JSON from *path* if it exists, otherwise return ``None``.

    ``path`` is expected to be a file.  Errors are propagated if the file
    cannot be parsed.
    """
    if path.is_file():
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    return None

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

    Supports both legacy single‑file JSON definitions and the newer folder‑based SDK.
    Raises ``FileNotFoundError`` if no definition is found.
    """
    # Prefer folder‑based definition (multi‑file SDK).
    dir_path = BASE_DIR / proc_id
    if dir_path.is_dir():
        # Load mandatory config.json – contains basic metadata.
        config_path = dir_path / "config.json"
        config = _load_json(config_path)
        if config is None:
            raise FileNotFoundError(f"Folder procedure '{proc_id}' missing config.json")
        # Normalise keys to match legacy expectations.
        result: Dict[str, Any] = {}
        result.update(config)
        if "procedure_id" in result:
            result["id"] = result.pop("procedure_id")
        if "display_name" in result:
            result["name"] = result.pop("display_name")
        # Load optional components.
        phases = _load_json(dir_path / "phases.json")
        if phases is not None:
            result["phases"] = phases
        for fname, key in [
            ("anatomy.json", "anatomy"),
            ("instruments.json", "instruments"),
            ("cards.json", "cards"),
            ("complications.json", "complications"),
            ("scoring.json", "scoring"),
            ("hidden.json", "hidden"),
            ("patient_variants.json", "patient_variants"),
        ]:
            part = _load_json(dir_path / fname)
            if part is not None:
                result[key] = part
        return result

    # Fallback to legacy single JSON file.
    path = _procedure_path(proc_id)
    if not path.is_file():
        raise FileNotFoundError(f"Procedure {proc_id!r} not found")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def list_procedures() -> Dict[str, Dict[str, Any]]:
    """Return a mapping of procedure_id → definition for all procedures.

    Supports both legacy single‑file JSON definitions and the new folder‑based SDK.
    Folder‑based definitions take precedence if a name clash occurs.
    """
    procedures: Dict[str, Dict[str, Any]] = {}
    # Load legacy .json files first.
    for file in BASE_DIR.glob("*.json"):
        proc_id = file.stem
        procedures[proc_id] = get_procedure(proc_id)
    # Then load folder‑based definitions, overriding any duplicates.
    for entry in BASE_DIR.iterdir():
        if entry.is_dir():
            config_path = entry / "config.json"
            if config_path.is_file():
                proc_id = entry.name
                procedures[proc_id] = get_procedure(proc_id)
    return procedures
