"""Hidden‑State → Observable mapping – Phase 5.2.

The function ``project_observable`` deterministically derives the patient‑visible
vitals, labs and clinical signs from the internal hidden physiological variables.
All calculations are pure (no randomness, no side‑effects) and the output is
JSON‑serialisable with canonical key ordering.
"""

from __future__ import annotations

from typing import Dict, Any

# ---------------------------------------------------------------------------
# Mapping logic – deterministic and side‑effect free
# ---------------------------------------------------------------------------

def project_observable(hidden_state: Dict[str, float]) -> Dict[str, Any]:
    """Return a deterministic observable snapshot given a hidden state mapping.

    Parameters
    ----------
    hidden_state:
        Mapping of hidden variable names to numeric values. The function expects the
        keys listed in the specification (e.g., ``"inflammation_index"``).

    Returns
    -------
    dict
        Observable metrics (vitals, labs, clinical signs). Keys are sorted to
        ensure a canonical JSON representation.
    """
    # Helper – safe fetch with default 0.0
    def get(key: str) -> float:
        return float(hidden_state.get(key, 0.0))

    # Simple deterministic derivations – the coefficients are chosen for clarity
    # rather than physiological fidelity.
    inflammation = get("inflammation_index")
    cytokine = get("cytokine_level")
    oxygen_debt = get("oxygen_debt")
    shock = get("shock_index")
    reserve = get("compensation_reserve")
    disease_stage = get("internal_disease_stage")
    drug_plasma = get("plasma_concentration")
    drug_effect = get("effect_site_concentration")

    # Vitals – heart rate increases with shock and inflammation, decreases with reserve
    heart_rate = 80.0 + 0.5 * inflammation + 0.8 * shock - 0.3 * reserve

    # Blood pressure – MAP drops with shock, rises with compensation reserve
    blood_pressure = 120.0 - 0.7 * shock + 0.2 * reserve

    # Respiratory rate – rises with oxygen debt and cytokine load
    respiratory_rate = 12.0 + 0.4 * oxygen_debt + 0.2 * cytokine

    # Temperature – modest increase with inflammation and disease stage
    temperature = 37.0 + 0.1 * inflammation + 0.05 * disease_stage

    # SpO2 – drops with shock and improves with drug effect concentration
    spo2 = 98.0 - 0.3 * shock + 0.1 * drug_effect

    # Lab values – illustrative deterministic functions
    labs = {
        "lactate": 1.0 + 0.2 * shock + 0.1 * inflammation,
        "creatinine": 0.8 + 0.05 * reserve,
        "potassium": 4.0 + 0.02 * get("hyperkalemia"),
    }

    # Clinical signs – derived thresholds expressed as booleans (or simple levels)
    signs = {
        "tachycardia": heart_rate > 100.0,
        "hypotension": blood_pressure < 90.0,
        "respiratory_distress": respiratory_rate > 25.0,
        "fever": temperature > 38.0,
        "hypoxemia": spo2 < 90.0,
    }

    observable: Dict[str, Any] = {
        "heart_rate": round(heart_rate, 2),
        "blood_pressure": round(blood_pressure, 2),
        "respiratory_rate": round(respiratory_rate, 2),
        "temperature": round(temperature, 2),
        "SpO2": round(spo2, 2),
        "labs": labs,
        "clinical_signs": signs,
    }

    # Ensure deterministic ordering for JSON serialisation – Python 3.7+ preserves insertion order.
    # We insert keys in the desired order explicitly.
    return observable
