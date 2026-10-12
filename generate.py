"""Generate synthetic blood panels plus ground-truth labels.
 
Each panel is a messy CSV (aliases, odd casing, decimal commas, a few bad rows).
Alongside the CSVs, ground_truth.json records what the correct answer is for
every pattern: "flagged", "not_flagged" or "insufficient_data".
 
Synthetic data only. The thresholds are simplified demo rules, not clinical advice.
"""

import csv
import json
import random
from pathlib import Path

from markers import MARKERS, units

OUT_DIR = Path(__file__).parent / "data" / "panels" # path to the output folder

STATUSES = ("flagged", "not_flagged", "insufficient_data") # possible statuses for the markers

# Each pattern lists the markers it needs, the rule that decides "flagged",
# and the value ranges used to generate panels for each status.

PATTERNS = {
    "dysglycemia": {
        "markers": ("glucose_fasting", "hba1c"),
        "rule": lambda v: v["glucose_fasting"] >= 100 and v["hba1c"] >= 5.7,
        "flagged": {
           "glucose_fasting": (100, 125),
           "hba1c": (5.7, 6.4),
        },
        "not_flagged": {
           "glucose_fasting": (70, 99),
           "hba1c": (4.0, 5.6),
        },
    },
    "atherogenic_dyslipidemia": {
        "requires": ("triglycerides", "hdl"),
        "rule": lambda v: v["triglycerides"] >= 150 and v["hdl"] < 40,
        "flagged": {
           "triglycerides": (160, 400),
           "hdl": (25, 38),
        },
        "not_flagged": {
           "triglycerides": (60, 140),
           "hdl": (45, 80),
        },
    },
    "iron_deficiency": {
        "requires": ("ferritin",),
        "rule": lambda v: v["ferritin"] < 30,
        "flagged": {
           "ferritin": (5, 28),
        },
        "not_flagged": {
           "ferritin": (50, 250),
        },
    },
}

# Healthy-looking values for markers that no pattern uses ("filler").
# Makes panels look realistic and give us markers for bad rows.
FILLER_RANGES = {
    "creatinine": (0.6, 1.2),
    "uric_acid": (3.0, 6.5),
    "vitamin_d": (25, 60),
    "tsh": (0.5, 3.5),
    "hscrp": (0.2, 2.5),
}

# Ways a row can be unresolvable. The validator must reject every one of them.
CORRUPTIONS = ("missing_unit", "wrong_unit", "not_a_number", "implausible")

# Early fail if this file and markers.py disagree on what markers exist.
for pattern in PATTERNS.values():
    for marker in pattern["requires"]:
        if marker not in MARKERS:
            raise ValueError(f"Pattern requires unknown marker: {marker}")

for marker in FILLER_RANGES:
    assert marker in MARKERS, f"Filler range for unknown marker: {marker}"

def label(values):
    """Ground truth for every pattern, given a dict of {marker : values} of VALID values."""
    truth = {}
    for name, pattern in PATTERNS.items():
        if any(marker not in values for marker in pattern["requires"]):
            truth[name] = "insufficient_data"
        else:
            truth[name] = "flagged" if pattern["rule"](values) else "not_flagged"
    return truth

def sample(rng, low, high): # sample a random value in the range, rounded to 1 decimal place
    return round(random.uniform(low, high), 1)

# --------- turning clean values into realistic/messy csv panels ---------

def panel_name(rng, marker):
    alias = rng.choice(sorted(MARKERS[marker]["aliases"])) # choose a random alias for the marker
    alias = rng.choice([str.lower, str.upper, str.title])(alias) # randomly change the case of the alias
    return rng.choice(["", " "]) + alias + rng.choice(["", " "]) # add random spaces before and after the alias to simulate messy input

def panel_value(rng, value):
    text = f"{value:.1f}" # format the value to 1 decimal place
    return text.replace(".", ",") if rng.random() < 0.5 else text # randomly replace decimal point with comma to simulate messy input

def panel_unit(rng, marker):
    unit = MARKERS[marker]["canonical_unit"] # get the canonical unit for the marker
    return rng.choice([unit, unit.upper(), f"{unit} "]) # randomly change the case of the unit and add a space after it

def makes_row(rng, marker, value):
    """Make a single row for a CSV panel, with random alias, value formatting, and unit."""
    return {
        "marker": panel_name(rng, marker),
        "value": panel_value(rng, value),
        "unit": panel_unit(rng, marker),
    }

def corrupt_row(rng, row, kind):
    """Corrupt a row in one of several ways, to test the validator."""
    row = dict(row) # copy the row so we don't modify the original
    if kind == "missing_unit":
        row["unit"] = rng.choice(["", " ", None]) # remove the unit
    elif kind == "wrong_unit":
        row["unit"] = rng.choice(["mg/l", "mmol/l", "g/dl"]) # replace the unit with a wrong one
    elif kind == "not_a_number":
        row["value"] = rng.choice(["abc", "NaN", "", "<0.5", ]) # replace the value with a non-numeric string
    else: # implausible
        row["value"] = "9999.0" # replace the value with an implausible number
    return row

def make_row(rng):
    """Make a single row for a CSV panel, with random alias, value formatting, and unit."""
    marker = rng.choice(list(MARKERS.keys())) # choose a random marker
    value = sample(rng, *MARKERS[marker]["plausible_range"]) # sample a plausible value for the marker
    return {
        "marker": panel_name(rng, marker),
        "value": panel_value(rng, value),
        "unit": panel_unit(rng, marker),
    }

# ------- one panel ------------

