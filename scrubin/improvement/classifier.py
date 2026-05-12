from .patches import Patch


def classify_findings(findings):
    categories = {
        "physiology": [],
        "procedure": [],
        "causality": [],
        "recovery": [],
        "structure": [],
    }
    fixability = {
        "config_fixable": [],
        "logic_fixable": [],
    }

    for f in findings:
        msg = f.message.lower()
        if "no vitals monitoring" in msg or "recovery window" in msg or "no procedure administered" in msg:
            categories["recovery"].append(f)
            if "no vitals monitoring" in msg:
                fixability["logic_fixable"].append(("recovery", f))
            else:
                fixability["config_fixable"].append(("recovery", f))
        elif "no clinical response" in msg or "no follow-up vitals" in msg or "follow-up vitals" in msg or "causal" in msg or "matching complication" in msg:
            categories["causality"].append(f)
            if "follow-up vitals" in msg:
                fixability["logic_fixable"].append(("causality", f))
            elif "no clinical response" in msg:
                fixability["config_fixable"].append(("causality", f))
            else:
                fixability["config_fixable"].append(("causality", f))
        elif "procedure" in msg and "administered" not in msg and "follow-up" not in msg:
            categories["procedure"].append(f)
            fixability["config_fixable"].append(("procedure", f))
        elif "hypoxia" in msg or "tachycardia" in msg or "bradycardia" in msg or "hypertensive" in msg or "hypotension" in msg:
            categories["physiology"].append(f)
            fixability["config_fixable"].append(("physiology", f))
        else:
            categories["structure"].append(f)

    return categories, fixability
