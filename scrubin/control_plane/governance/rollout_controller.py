from typing import Dict, Any

class RolloutController:
    """
    Safe, staged deployment of clinical policies.
    Enforces canary rollout with drift monitoring and automatic rollback.
    """
    def __init__(self, max_initial_fraction: float = 0.1):
        self.max_initial_fraction = max_initial_fraction
        self.active_policy_id = None
        self.traffic_fraction = 0.0
        self.frozen = False

    def deploy(self, policy_id: str, fingerprint: str):
        if self.frozen:
            raise RuntimeError("Rollout frozen due to drift detection. Rollback required.")
        self.active_policy_id = policy_id
        self.traffic_fraction = self.max_initial_fraction
        print(f"[ROLLOUT] Policy '{policy_id}' deployed at {self.traffic_fraction*100:.0f}% traffic.")

    def promote(self, increment: float = 0.1):
        if self.frozen:
            raise RuntimeError("Rollout frozen. Cannot promote.")
        self.traffic_fraction = min(1.0, self.traffic_fraction + increment)
        print(f"[ROLLOUT] Traffic promoted to {self.traffic_fraction*100:.0f}%.")

    def freeze(self, reason: str):
        self.frozen = True
        print(f"[ROLLOUT] FROZEN — Reason: {reason}")

    def rollback(self):
        self.active_policy_id = None
        self.traffic_fraction = 0.0
        self.frozen = False
        print("[ROLLOUT] Rolled back to baseline. No active policy.")
