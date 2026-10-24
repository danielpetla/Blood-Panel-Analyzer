"""Deterministic baseline: applies the threshold rules with plain Python, no LLM.

Input: list of LabResult (already validated by schema.py).
Output: {pattern: "flagged" | "not_flagged" | "insufficient_data"}"""

# The rule is a lambda: a one-line function that gets a dict {marker: value}
# and returns True when the pattern should be flagged.
RULES = {
    "dysglycemia": (
        ("glucose_fasting", "hba1c"),
        lambda v: v["glucose_fasting"] >= 100 and v["hba1c"] >= 5.7,
    ),
    "atherogenic_dyslipidemia": (
        ("triglycerides", "hdl"),
        lambda v: v["triglycerides"] >= 150 and v["hdl"] < 40,
    ),
    "iron_deficiency": (("ferritin",), lambda v: v["ferritin"] < 30),
}
# Turn the list of LabResult objects into a simple dict


def analyze_rules(accepted):
    v = {r.marker: r.value for r in accepted}
    out = {}
    for name, (req, rule) in RULES.items():
        # Check for missing markers FIRST. Running the rule on a missing marker
        if any(m not in v for m in req):
            out[name] = "insufficient_data"
        else:
            # All needed markers are present, so the rule can be evaluated safely.
            out[name] = "flagged" if rule(v) else "not_flagged"
    return out
