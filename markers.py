MARKERS = {
    "glucose_fasting": {
        "canonical_unit": "mg/dl",  # standard unit for the marker
        "aliases": {
            "glucose",
            "fasting glucose",
            "glucose (fasting)",
            "nüchternglukose",
        },  # other names for the marker
        "plausible_range": (20, 800),  # marker possible number range
    },
    "hba1c": {
        "canonical_unit": "%",
        "aliases": {"hba1c", "a1c", "hemoglobin a1c", "hämoglobin a1c"},
        "plausible_range": (3, 20),
    },
    "total_cholesterol": {
        "canonical_unit": "mg/dl",
        "aliases": {"total cholesterol", "cholesterin gesamt", "gesamtcholesterin"},
        "plausible_range": (50, 700),
    },
    "hdl": {
        "canonical_unit": "mg/dl",
        "aliases": {"hdl", "hdl-c", "hdl-cholesterin"},
        "plausible_range": (5, 200),
    },
    "ldl": {
        "canonical_unit": "mg/dl",
        "aliases": {"ldl", "ldl-c", "ldl-cholesterin"},
        "plausible_range": (5, 600),
    },
    "triglycerides": {
        "canonical_unit": "mg/dl",
        "aliases": {"triglycerides", "tg", "triglyceride"},
        "plausible_range": (10, 2000),
    },
    "hscrp": {
        "canonical_unit": "mg/l",
        "aliases": {"hs-crp", "crp hochsensitiv", "c-reactive protein, hs"},
        "plausible_range": (0, 500),
    },
    "ferritin": {
        "canonical_unit": "ng/ml",
        "aliases": {"ferritin", "serum ferritin"},
        "plausible_range": (1, 5000),
    },
    "vitamin_d": {
        "canonical_unit": "ng/ml",
        "aliases": {"25-oh vitamin d", "25(oh)d", "25-oh-vitamin d"},
        "plausible_range": (1, 250),
    },
    "tsh": {
        "canonical_unit": "miu/l",
        "aliases": {"tsh", "thyrotropin", "tsh basal"},
        "plausible_range": (0, 150),
    },
    "creatinine": {
        "canonical_unit": "mg/dl",
        "aliases": {"creatinine", "kreatinin"},
        "plausible_range": (0.2, 15),
    },
    "uric_acid": {
        "canonical_unit": "mg/dl",
        "aliases": {"uric acid", "urate", "harnsäure"},
        "plausible_range": (0.5, 20),
    },
}

ALIAS_TO_MARKER = {
    alias: key  # associating the alias to the "main" key
    for key, info in MARKERS.items()  # enter the outer dict
    for alias in info["aliases"]  # enter the aliases set
}


def normalize_name(name):
    return name.lower().strip()  # normalize the input to avoid error


def find_marker(name):
    # get the marker name associated with the alias
    return ALIAS_TO_MARKER.get(normalize_name(name))


def units(marker):   # return the canonical unit for the marker
    if marker not in MARKERS:
        return None
    return MARKERS[marker]["canonical_unit"]
