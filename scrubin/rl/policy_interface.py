'''RL policy interface – deterministic action submission.'''\n\nfrom __future__ import annotations\nimport hashlib\nfrom dataclasses import dataclass\nfrom typing import Dict, Any\n\nfrom scrubin.events.event import SurgicalEvent\n\n# Define a simple set of allowed actions for the placeholder – could be extended\nALLOWED_ACTION_TYPES = {"noop", "administer_med", "assign_bed", "escalate"}\n\n@dataclass(frozen=True)\nclass PolicyAction:\n    action_type: str\n    target_patient_id: str\n    parameters: Dict[str, Any]\n    deterministic_id: str\n\n    @staticmethod\n    def from_raw(action_type: str, target_patient_id: str, parameters: Dict[str, Any], tick: int) -> "PolicyAction":\n        # Compute deterministic ID from fields – no UUIDs\n        data = f"{action_type}:{target_patient_id}:{sorted(parameters.items())}:{tick}"
        deterministic_id = hashlib.sha256(data.encode()).hexdigest()
        return PolicyAction(action_type=action_type, target_patient_id=target_patient_id, parameters=parameters, deterministic_id=deterministic_id)
\ndef validate_action(action: PolicyAction, snapshot) -> None:\n    """Validate that the action is permissible for the given snapshot.
\n    Placeholder implementation – raises ``ValueError`` if ``action_type`` not in allowed set.
    """
    if action.action_type not in ALLOWED_ACTION_TYPES:
        raise ValueError(f"Invalid action type: {action.action_type}")\n    # Additional validation against snapshot could be added here\n\ndef action_to_event(action: PolicyAction, tick: int) -> SurgicalEvent:\n    """Convert a validated PolicyAction into a ``SurgicalEvent`` for the simulation.
\n    The event_type mirrors the action_type; payload includes patient id and parameters.
    """
    # No validation here – caller should have invoked ``validate_action``
    return SurgicalEvent(
        tick=tick,
        event_type=action.action_type,
        payload={"patient_id": action.target_patient_id, "parameters": action.parameters, "deterministic_id": action.deterministic_id},
    )\n