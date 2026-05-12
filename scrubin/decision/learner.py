import json
import os
from dataclasses import dataclass, asdict

WEIGHTS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "improvement", "policy_weights.json")
)

MIN_SAMPLES = 5
LEARNING_RATE = 0.05
CLAMP_MIN = -50.0
CLAMP_MAX = 50.0
MAX_SIGN_FLIP = 5.0


@dataclass
class PolicyWeights:
    resolves_complication: float = 20.0
    improves_vitals: float = 10.0
    unnecessary_penalty: float = -15.0
    duplicate_penalty: float = -10.0
    recovery_window_bonus: float = 5.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PolicyWeights":
        return cls(
            resolves_complication=d.get("resolves_complication", 20.0),
            improves_vitals=d.get("improves_vitals", 10.0),
            unnecessary_penalty=d.get("unnecessary_penalty", -15.0),
            duplicate_penalty=d.get("duplicate_penalty", -10.0),
            recovery_window_bonus=d.get("recovery_window_bonus", 5.0),
        )

    def save(self, path: str = None):
        path = path or WEIGHTS_PATH
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str = None) -> "PolicyWeights":
        path = path or WEIGHTS_PATH
        if not os.path.exists(path):
            return cls()
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


def _extract_features(decision_payload, validation_payload, execution_payload):
    features = {
        "resolves_complication": False,
        "improves_vitals": False,
        "unnecessary": False,
        "duplicate": False,
        "in_recovery_window": False,
    }
    action = decision_payload.get("action", {})
    reasoning = decision_payload.get("reasoning", [])
    action_target = action.get("target", "")
    action_type = action.get("type", "")

    if action_type == "procedure" and action_target not in ("vitals", "vitals_improvement", "none"):
        features["resolves_complication"] = True

    for r in reasoning:
        if "improves" in r.lower() or "oxygenation" in r.lower() or "blood pressure" in r.lower() or "heart rate" in r.lower() or "fever" in r.lower():
            features["improves_vitals"] = True
        if "unnecessary" in r.lower():
            features["unnecessary"] = True
        if "duplicate" in r.lower() or "duplicates" in r.lower():
            features["duplicate"] = True
        if "recovery window" in r.lower():
            features["in_recovery_window"] = True

    return features


def _clamp(value, lo=CLAMP_MIN, hi=CLAMP_MAX):
    return max(lo, min(hi, value))


def _safe_update(current, delta):
    new_val = current + delta
    if current >= 0 and new_val < 0 and abs(delta) > MAX_SIGN_FLIP:
        new_val = 0.0
    elif current <= 0 and new_val > 0 and abs(delta) > MAX_SIGN_FLIP:
        new_val = 0.0
    return _clamp(new_val)


class PolicyLearner:
    def __init__(self, learning_rate: float = LEARNING_RATE,
                 min_samples: int = MIN_SAMPLES,
                 weights_path: str = None):
        self._lr = learning_rate
        self._min_samples = min_samples
        self._weights_path = weights_path or WEIGHTS_PATH
        self._update_log: list[dict] = []

    def update_from_history(self, ledger_events) -> PolicyWeights:
        decisions = [e for e in ledger_events if e.type == "decision"]
        validations = [e for e in ledger_events if e.type == "decision_validation"]
        executions = [e for e in ledger_events if e.type == "decision_execution"]

        val_by_tick = {v.tick: v.payload for v in validations}
        exec_by_tick = {x.tick: x.payload for x in executions}

        samples = []
        for d in decisions:
            tick = d.tick
            v = val_by_tick.get(tick)
            x = exec_by_tick.get(tick)
            if v is None:
                continue
            if v.get("confidence") != "high":
                continue
            if x is None or not x.get("executed"):
                continue

            features = _extract_features(d.payload, v, x)
            weighted_delta = v.get("weighted_delta", 0.0)
            samples.append((features, weighted_delta))

        weights = PolicyWeights.load(self._weights_path)
        old_weights = weights.to_dict()

        if len(samples) < self._min_samples:
            return weights

        feature_key_map = {
            "resolves_complication": "resolves_complication",
            "improves_vitals": "improves_vitals",
            "unnecessary": "unnecessary_penalty",
            "duplicate": "duplicate_penalty",
            "in_recovery_window": "recovery_window_bonus",
        }

        weight_deltas = {k: 0.0 for k in feature_key_map.values()}

        for features, wdelta in samples:
            sign = 1.0 if wdelta > 0 else -1.0
            magnitude = abs(wdelta) / 100.0
            for feat_key, weight_key in feature_key_map.items():
                if features.get(feat_key):
                    base = getattr(weights, weight_key)
                    if base >= 0:
                        weight_deltas[weight_key] += sign * magnitude * self._lr
                    else:
                        weight_deltas[weight_key] -= sign * magnitude * self._lr

        n = len(samples)
        for weight_key, total_delta in weight_deltas.items():
            avg_delta = total_delta / n
            current = getattr(weights, weight_key)
            new_val = _safe_update(current, avg_delta)
            setattr(weights, weight_key, round(new_val, 2))

        new_weights = weights.to_dict()

        self._update_log.append({
            "old_weights": old_weights,
            "new_weights": new_weights,
            "weight_deltas": {k: round(v / n, 4) for k, v in weight_deltas.items()},
            "samples_used": n,
        })

        weights.save(self._weights_path)
        return weights

    def apply_to_engine(self, engine, weights: PolicyWeights = None):
        if weights is None:
            weights = PolicyWeights.load(self._weights_path)
        engine._policy_weights = weights

    @property
    def update_log(self) -> list[dict]:
        return list(self._update_log)

    def to_dict(self) -> dict:
        return {
            "learning_rate": self._lr,
            "min_samples": self._min_samples,
            "update_count": len(self._update_log),
        }
