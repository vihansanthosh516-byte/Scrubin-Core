"""Event type constants used throughout the deterministic event system.

Each constant is a snake_case string that uniquely identifies a particular
clinical or simulation event.  New event types can be added here without
changing the rest of the engine.
"""

# Bleeding and blood‑loss handling
BLEEDING_EVENT = "bleeding_event"
# Generic action event – emitted when a user or planner action is turned into an event
ACTION_EVENT = "action_event"
# Visibility degradation (e.g., due to blood, smoke, etc.)
VISIBILITY_EVENT = "visibility_event"
# Inflammation arising from thermal or chemical injury
INFLAMMATION_EVENT = "inflammation_event"
# Sepsis development
SEPSIS_EVENT = "sepsis_event"
# Hypotension flag
HYPOTENSION_EVENT = "hypotension_event"
# Generic placeholder for any other events that may be added later
# (e.g., thermal_injury_event, contamination_event, etc.)
