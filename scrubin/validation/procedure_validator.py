"""Core procedure validation logic used by the CLI script and unit tests.

The validator walks each folder under ``scrubin/procedures`` and checks:

* required files are present
* JSON schemas for config, phases, anatomy, instruments, cards, complications,
  scoring, hidden
* cross‑reference integrity (cards reference existing phases, anatomy,
  instruments, complications, outcome IDs, etc.)
* a simple directed phase graph derived from card outcomes is well‑formed:
  exactly one entry phase, all phases reachable, dead‑end warnings.

All error and warning collections are sorted to guarantee deterministic output –
running the validator twice on the same repository yields identical stdout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Iterable

# ---------------------------------------------------------------------------
# Helper utilities – deterministic loading & sorting
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Dict:
    """Load *path* as JSON, raising RuntimeError on failure."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSON file {path}: {exc}") from exc

def _sorted(items: Iterable[str]) -> List[str]:
    """Return a sorted list of strings (deterministic order)."""
    return sorted(items)

# ---------------------------------------------------------------------------
# Core validator for a single procedure directory
# ---------------------------------------------------------------------------

class ProcedureValidator:
    """Validate a folder‑based Scrubin procedure package.

    The validator is deliberately stateless – all information is derived from the
    files on disk.  ``validate`` returns ``(passed, errors, warnings)`` where
    ``passed`` is ``True`` only if *no* error was recorded.
    """

    REQUIRED_FILES = [
        "config.json",
        "phases.json",
        "anatomy.json",
        "instruments.json",
        "cards.json",
        "complications.json",
        "scoring.json",
        "hidden.json",
    ]
    OPTIONAL_FILES = [
        "patient_profiles.json",
        "variants.json",
        "patient_variants.json",
        "tutorial.json",
        "ai_tutor.json",
        "voice.json",
        "checkpoints.json",
    ]

    def __init__(self, root: Path, global_ids: Set[str] | None = None):
        self.root = root
        self.global_ids = global_ids if global_ids is not None else set()

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        errors: List[str] = []
        warnings: List[str] = []
        # ----- 1. folder structure -----
        present = {p.name for p in self.root.iterdir() if p.is_file()}
        for f in self.REQUIRED_FILES:
            if f not in present:
                errors.append(f"Missing required file {f}")
        for f in self.OPTIONAL_FILES:
            if f not in present:
                warnings.append(f"Missing optional file {f}")
        if errors:
            return False, errors, warnings
        # ----- 2. load JSON -----
        try:
            cfg = _load_json(self.root / "config.json")
            phases = _load_json(self.root / "phases.json")
            anatomy = _load_json(self.root / "anatomy.json")
            instruments = _load_json(self.root / "instruments.json")
            cards = _load_json(self.root / "cards.json")
            complications = _load_json(self.root / "complications.json")
            scoring = _load_json(self.root / "scoring.json")
            hidden = _load_json(self.root / "hidden.json")
            patient_variants = None
            if (self.root / "patient_variants.json").is_file():
                patient_variants = _load_json(self.root / "patient_variants.json")
        except RuntimeError as exc:
            errors.append(str(exc))
            return False, errors, warnings
        # ----- 3. component validation -----
        self._validate_config(cfg, errors, warnings)
        phase_ids = self._validate_phases(phases, errors, warnings)
        anatomy_ids = self._validate_anatomy(anatomy, errors, warnings)
        instrument_ids = self._validate_instruments(instruments, errors, warnings)
        complication_ids = self._validate_complications(complications, errors, warnings)
        self._validate_scoring(scoring, errors, warnings)
        self._validate_hidden(hidden, errors, warnings)
        self._validate_patient_variants(patient_variants, errors, warnings)
        self._validate_cards(
            cards,
            phase_ids,
            anatomy_ids,
            instrument_ids,
            complication_ids,
            errors,
            warnings,
        )
        # ----- 4. phase graph -----
        self._validate_phase_graph(cards, phase_ids, errors, warnings)
        return not errors, errors, warnings

    # ---------------------------------------------------------------------
    # component validators
    # ---------------------------------------------------------------------
    def _validate_config(self, cfg: Dict, errors: List[str], warnings: List[str]):
        required = ["procedure_id", "display_name", "category", "description", "version"]
        for k in required:
            if k not in cfg:
                errors.append(f"config.json missing required key '{k}'")
        proc_id = cfg.get("procedure_id") or cfg.get("id")
        if proc_id:
            if proc_id in self.global_ids:
                errors.append(f"Duplicate procedure id '{proc_id}' across repository")
            else:
                self.global_ids.add(proc_id)
        else:
            errors.append("config.json does not contain a procedure identifier (procedure_id or id)")

    def _validate_phases(self, phases: List[Dict], errors: List[str], warnings: List[str]) -> Set[str]:
        if not isinstance(phases, list):
            errors.append("phases.json must be a list")
            return set()
        ids: Set[str] = set()
        for idx, ph in enumerate(phases):
            if not isinstance(ph, dict):
                errors.append(f"Phase #{idx} is not an object")
                continue
            for field in ["id", "name", "description"]:
                if field not in ph:
                    errors.append(f"Phase {ph.get('id', f'#{idx}')} missing required field '{field}'")
            pid = ph.get("id")
            if pid:
                if pid in ids:
                    errors.append(f"Duplicate phase id '{pid}'")
                else:
                    ids.add(pid)
        if not ids:
            errors.append("No valid phases defined")
        return ids

    def _validate_anatomy(self, anatomy: Dict, errors: List[str], warnings: List[str]) -> Set[str]:
        structs = anatomy.get("structures")
        if not isinstance(structs, list):
            errors.append("anatomy.json must contain a 'structures' list")
            return set()
        ids: Set[str] = set()
        for idx, obj in enumerate(structs):
            if not isinstance(obj, dict):
                errors.append(f"Anatomy entry #{idx} is not an object")
                continue
            for field in ["id", "name", "type"]:
                if field not in obj:
                    errors.append(f"Anatomy entry missing required field '{field}' (index {idx})")
            aid = obj.get("id")
            if aid:
                if aid in ids:
                    errors.append(f"Duplicate anatomy ID '{aid}'")
                else:
                    ids.add(aid)
        return ids

    def _validate_instruments(self, instruments: Dict, errors: List[str], warnings: List[str]) -> Set[str]:
        lst = instruments.get("instruments")
        if not isinstance(lst, list):
            errors.append("instruments.json must contain an 'instruments' list")
            return set()
        ids: Set[str] = set()
        for idx, obj in enumerate(lst):
            if not isinstance(obj, dict):
                errors.append(f"Instrument entry #{idx} is not an object")
                continue
            for field in ["id", "name"]:
                if field not in obj:
                    errors.append(f"Instrument entry missing required field '{field}' (index {idx})")
            iid = obj.get("id")
            if iid:
                if iid in ids:
                    errors.append(f"Duplicate instrument ID '{iid}'")
                else:
                    ids.add(iid)
        return ids

    def _validate_complications(self, comps: List[Dict], errors: List[str], warnings: List[str]) -> Set[str]:
        if not isinstance(comps, list):
            errors.append("complications.json must be a list")
            return set()
        ids: Set[str] = set()
        for idx, comp in enumerate(comps):
            if not isinstance(comp, dict):
                errors.append(f"Complication entry #{idx} is not an object")
                continue
            if "id" not in comp:
                errors.append(f"Complication entry #{idx} missing required key 'id'")
                continue
            cid = comp["id"]
            if cid in ids:
                errors.append(f"Duplicate complication ID '{cid}'")
            else:
                ids.add(cid)
        return ids

    def _validate_scoring(self, scoring: Dict, errors: List[str], warnings: List[str]):
        if not isinstance(scoring, dict):
            errors.append("scoring.json must be an object")
            return
        if "max_score" not in scoring:
            errors.append("scoring.json missing required key 'max_score'")
        # further sanity checks can be added later

    def _validate_hidden(self, hidden: Dict, errors: List[str], warnings: List[str]):
        if not isinstance(hidden, dict):
            errors.append("hidden.json must be a JSON object")
        # Validate patient_variants.json if present
    def _validate_patient_variants(self, variants, errors, warnings):
        """Validate patient_variants.json if present."""
        if variants is None:
            return
        if not isinstance(variants, list):
            errors.append("patient_variants.json must be a list")
            return
        ids = set()
        for idx, var in enumerate(variants):
            if not isinstance(var, dict):
                errors.append(f"Variant #{idx} is not an object")
                continue
            # required fields
            for field in ["id", "display_name", "description", "difficulty"]:
                if field not in var:
                    errors.append(f"Variant #{idx} missing required key '{field}'")
            vid = var.get("id")
            if vid:
                if vid in ids:
                    errors.append(f"Duplicate variant id '{vid}'")
                else:
                    ids.add(vid)
            # difficulty numeric > 0
            diff = var.get("difficulty")
            if diff is not None:
                if not isinstance(diff, (int, float)):
                    errors.append(f"Variant '{vid}' difficulty must be numeric")
                elif diff <= 0:
                    errors.append(f"Variant '{vid}' difficulty must be > 0")
            # optional dict fields
            for opt_key in ["physiology", "hidden_state", "complication_modifiers"]:
                if opt_key in var and not isinstance(var[opt_key], dict):
                    errors.append(f"Variant '{vid}' field '{opt_key}' must be an object")
        # Deterministic ordering warning
        sorted_ids = sorted(ids)
        actual_ids = [var.get("id") for var in variants if isinstance(var, dict) and "id" in var]
        if actual_ids != sorted_ids:
            warnings.append("patient_variants.json is not sorted by id; consider sorting for deterministic order")

    def _validate_cards(
        self,
        cards: List[Dict],
        phase_ids: Set[str],
        anatomy_ids: Set[str],
        instrument_ids: Set[str],
        complication_ids: Set[str],
        errors: List[str],
        warnings: List[str],
    ) -> Set[str]:
        """Validate cards, collect outcome IDs for prerequisite checks."""
        if not isinstance(cards, list):
            errors.append("cards.json must be a list")
            return set()
        card_ids: Set[str] = set()
        outcome_ids: Set[str] = set()
        for idx, card in enumerate(cards):
            if not isinstance(card, dict):
                errors.append(f"Card entry #{idx} is not an object")
                continue
            cid = card.get("id")
            if not cid:
                errors.append(f"Card at index {idx} missing required key 'id'")
            else:
                if cid in card_ids:
                    errors.append(f"Duplicate card ID '{cid}'")
                else:
                    card_ids.add(cid)
            # phase reference
            ph = card.get("phase")
            if not ph:
                errors.append(f"Card '{cid}' missing required key 'phase'")
            elif ph not in phase_ids:
                errors.append(f"Card '{cid}' references unknown phase '{ph}'")
            # anatomy targets
            anat = card.get("anatomical_targets", [])
            if not isinstance(anat, list):
                errors.append(f"Card '{cid}' field 'anatomical_targets' must be a list")
            else:
                for a in anat:
                    if a not in anatomy_ids:
                        errors.append(f"Card '{cid}' references unknown anatomy '{a}'")
            # instrument targets
            instr = card.get("required_instruments", [])
            if not isinstance(instr, list):
                errors.append(f"Card '{cid}' field 'required_instruments' must be a list")
            else:
                for i in instr:
                    if i not in instrument_ids:
                        errors.append(f"Card '{cid}' references unknown instrument '{i}'")
            # possible outcomes
            outcomes = card.get("possible_outcomes", [])
            if not isinstance(outcomes, list):
                errors.append(f"Card '{cid}' field 'possible_outcomes' must be a list")
                continue
            for o_idx, out in enumerate(outcomes):
                if not isinstance(out, dict):
                    errors.append(f"Outcome #{o_idx} in card '{cid}' is not an object")
                    continue
                oid = out.get("id")
                if not oid:
                    errors.append(f"Outcome #{o_idx} in card '{cid}' missing required key 'id'")
                else:
                    if oid in outcome_ids:
                        errors.append(f"Duplicate outcome ID '{oid}' (card '{cid}')")
                    else:
                        outcome_ids.add(oid)
                nxt = out.get("next_phase")
                if nxt is not None and nxt not in phase_ids:
                    errors.append(f"Outcome '{oid}' in card '{cid}' references unknown next_phase '{nxt}'")
                comp_trig = out.get("complication_triggers", [])
                if comp_trig:
                    if not isinstance(comp_trig, list):
                        errors.append(f"Outcome '{oid}' in card '{cid}' has non‑list complication_triggers")
                    else:
                        for ct in comp_trig:
                            if ct not in complication_ids:
                                errors.append(f"Outcome '{oid}' in card '{cid}' references unknown complication '{ct}'")
        # prerequisites validation after outcome collection
        for card in cards:
            cid = card.get("id") or "<unknown>"
            prereqs = card.get("prerequisites", [])
            if not isinstance(prereqs, list):
                errors.append(f"Card '{cid}' field 'prerequisites' must be a list")
                continue
            for pre in prereqs:
                if pre not in outcome_ids:
                    errors.append(f"Card '{cid}' has prerequisite '{pre}' that does not match any outcome ID")
        return outcome_ids

    def _validate_phase_graph(
        self,
        cards: List[Dict],
        phase_ids: Set[str],
        errors: List[str],
        warnings: List[str],
    ):
        """Derive a directed graph from card outcomes and validate it."""
        outgoing: Dict[str, Set[str]] = {pid: set() for pid in phase_ids}
        incoming: Dict[str, Set[str]] = {pid: set() for pid in phase_ids}
        for card in cards:
            ph = card.get("phase")
            if not ph:
                continue
            for out in card.get("possible_outcomes", []):
                nxt = out.get("next_phase")
                if nxt is None:
                    continue
                if nxt not in phase_ids:
                    continue  # already reported
                outgoing[ph].add(nxt)
                incoming[nxt].add(ph)
        # entry phases
        entry = [pid for pid, inc in incoming.items() if not inc]
        if len(entry) == 0:
            errors.append("No entry phase found (every phase has an incoming edge)")
        elif len(entry) > 1:
            errors.append(f"Multiple entry phases detected: {', '.join(_sorted(entry))}")
        # reachability
        if entry:
            visited: Set[str] = set()
            stack: List[str] = [entry[0]]
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                stack.extend(outgoing.get(cur, []))
            unreachable = phase_ids - visited
            for pid in _sorted(unreachable):
                errors.append(f"Phase '{pid}' is unreachable from entry phase")
        # dead‑end detection (phases with no outgoing edges that are not terminal)
        terminal: Set[str] = set()
        for card in cards:
            ph = card.get("phase")
            for out in card.get("possible_outcomes", []):
                if out.get("next_phase") is None:
                    terminal.add(ph)
        for pid in phase_ids:
            if not outgoing.get(pid) and pid not in terminal:
                warnings.append(f"Phase '{pid}' is a dead‑end (no outgoing edges and not marked terminal)")

# ---------------------------------------------------------------------------
# Repository‑wide validation driver
# ---------------------------------------------------------------------------

def validate_all(repo_root: Path | None = None) -> Tuple[int, int, int, List[Tuple[str, bool, List[str], List[str]]]:
    """Validate every procedure folder under ``scrubin/procedures``.

    Returns ``(total, passed, failed, details)`` where *details* is a list of
    ``(name, ok, errors, warnings)``.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    proc_dir = repo_root / "scrubin" / "procedures"
    if not proc_dir.is_dir():
        raise RuntimeError(f"Procedures directory not found at {proc_dir}")
    global_ids: Set[str] = set()
    total = 0
    passed = 0
    failed = 0
    details: List[Tuple[str, bool, List[str], List[str]]] = []
    for entry in proc_dir.iterdir():
        if not entry.is_dir():
            continue
        total += 1
        validator = ProcedureValidator(entry, global_ids)
        ok, errs, warns = validator.validate()
        if ok:
            passed += 1
        else:
            failed += 1
        details.append((entry.name, ok, _sorted(errs), _sorted(warns)))
    return total, passed, failed, details
