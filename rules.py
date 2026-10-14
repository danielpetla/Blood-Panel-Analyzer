RULES = {
    "dysglycemia": (("glucose_fasting", "hba1c"), lambda v: v["glucose_fasting"] >= 100 and v["hba1c"] >= 5.7),
    "atherogenic_dyslipidemia": (("triglycerides", "hdl"), lambda v: v["triglycerides"] >= 150 and v["hdl"] < 40),
    "iron_deficiency": (("ferritin",), lambda v: v["ferritin"] < 30),
}
def analyze_rules(accepted):
    v = {r.marker: r.value for r in accepted}
    out = {}
    for name, (req, rule) in RULES.items():
        if any(m not in v for m in req):
            out[name] = "insufficient_data"
        else:
            out[name] = "flagged" if rule(v) else "not_flagged"
    return out