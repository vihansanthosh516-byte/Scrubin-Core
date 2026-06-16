"""Fast event processor used in benchmark mode.

The regular ``scrubin.events.event_processor.process_events`` function is already
pure and deterministic; it does not perform any logging or replay side‑effects.
For benchmark mode we simply re‑export the same implementation under a distinct
name to make the intent explicit and to allow future optimisations without
changing the orchestrator logic.
"""

from __future__ import annotations

from .event_processor import process_events  # noqa: F401 – re‑export
