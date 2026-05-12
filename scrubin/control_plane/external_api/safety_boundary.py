from typing import Dict, Any, List

class SafetyBoundary:
    """
    Hard Firewall for clinical telemetry: Prohibits external access to simulation internals.
    Only allows sanitized aggregates and policy-driven outcomes.
    """
    FORBIDDEN_KEYWORDS = {
        "causal_graph",
        "replay_snapshot",
        "kernel_internal",
        "raw_vitals",
        "node_id"
    }

    def sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep-inspects response for internal semantic leakage.
        """
        # simplified recursive sanitization
        sanitized = {}
        for k, v in response.items():
            if k in self.FORBIDDEN_KEYWORDS:
                continue
            if isinstance(v, dict):
                sanitized[k] = self.sanitize_response(v)
            else:
                sanitized[k] = v
        return sanitized
