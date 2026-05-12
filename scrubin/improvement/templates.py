TEMPLATES = {
    "clamp_vital": {
        "action": "modify",
        "description": "Clamp vital sign to prevent out-of-range values",
        "fields": ["target", "path", "value"],
    },
    "add_procedure_branch": {
        "action": "add",
        "description": "Add missing procedure branch for complication type",
        "fields": ["target", "path", "value"],
    },
    "widen_recovery_window": {
        "action": "modify",
        "description": "Extend recovery window for intervention timing",
        "fields": ["target", "path", "value"],
    },
    "fix_event_ordering": {
        "action": "modify",
        "description": "Enforce strict deterministic event ordering",
        "fields": ["target", "path", "value"],
    },
}
