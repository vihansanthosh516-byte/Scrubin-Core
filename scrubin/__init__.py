# Package initializer – intentionally minimal to avoid side‑effects during import.
# The original import of ``core.objective`` pulled in the orchestrator and engine
# modules, which in turn depended on components that are not needed for the unit
# tests in this repository.  Keeping the top‑level ``scrubin`` package lightweight
# ensures that importing sub‑modules (e.g. ``scrubin.world.state`` or the new
# runtime utilities) does not trigger unnecessary side‑effects or import errors.
