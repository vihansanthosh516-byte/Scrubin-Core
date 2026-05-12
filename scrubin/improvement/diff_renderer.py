from .patches import Patch


def render_patch(patch: Patch) -> str:
    lines = [
        f"--- {patch.target}",
        f"+++ {patch.target} (patched)",
        f"@@ {patch.path } @@",
        f"action: {patch.action}",
        f"value: {patch.value}",
        f"reason: {patch.reason}",
    ]
    return "\n".join(lines)


def render_patch_plan(patches: list) -> str:
    if not patches:
        return "No patches required. System is healthy."
    sections = []
    for i, p in enumerate(patches, 1):
        sections.append(f"Patch {i}:\n{render_patch(p)}")
    return "\n\n".join(sections)
