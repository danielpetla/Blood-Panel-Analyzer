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

OUT_DIR = Path(__file__).parent / "data" / \
    "panels"  # path to the output folder

# possible statuses for the markers
STATUSES = ("flagged", "not_flagged", "insufficient_data")

# Each pattern lists the markers it needs, the rule that decides "flagged",
# and the value ranges used to generate panels for each status.

PATTERNS = {
    "dysglycemia": {
        "requires": ("glucose_fasting", "hba1c"),
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
            truth[name] = "flagged" if pattern["rule"](
                values) else "not_flagged"
    return truth


def sample(rng, low, high):  # sample a random value in the range, rounded to 1 decimal place
    return round(rng.uniform(low, high), 1)

# --------- turning clean values into realistic/messy csv panels ---------


def panel_name(rng, marker):
    # choose a random alias for the marker
    alias = rng.choice(sorted(MARKERS[marker]["aliases"]))
    alias = rng.choice([str.lower, str.upper, str.title])(
        alias)  # randomly change the case of the alias
    # add random spaces before and after the alias to simulate messy input
    return rng.choice(["", " "]) + alias + rng.choice(["", " "])


def panel_value(rng, value):
    text = f"{value:.1f}"  # format the value to 1 decimal place
    # randomly replace decimal point with comma to simulate messy input
    return text.replace(".", ",") if rng.random() < 0.5 else text


def panel_unit(rng, marker):
    # get the canonical unit for the marker
    unit = MARKERS[marker]["canonical_unit"]
    # randomly change the case of the unit and add a space after it
    return rng.choice([unit, unit.upper(), f"{unit} "])


def makes_row(rng, marker, value):
    """Make a single row for a CSV panel, with random alias, value formatting, and unit."""
    return {
        "marker": panel_name(rng, marker),
        "value": panel_value(rng, value),
        "unit": panel_unit(rng, marker),
    }


def corrupt_row(rng, row, kind):
    """Corrupt a row in one of several ways, to test the validator."""
    row = dict(row)  # copy the row so we don't modify the original
    if kind == "missing_unit":
        row["unit"] = rng.choice(["", " ", None])  # remove the unit
    elif kind == "wrong_unit":
        canonical = units(marker)
        row["unit"] = rng.choice(
            [u for u in ("mg/l", "mmol/l", "g/dl", "ng/ml") if u != canonical])
    elif kind == "not_a_number":
        # replace the value with a non-numeric string
        row["value"] = rng.choice(["abc", "NaN", "", "<0.5", ])
    else:  # implausible
        row["value"] = "9999.0"  # replace the value with an implausible number
    return row


def make_unknown_row(rng):
    """Make a row for a marker that isn't in any pattern, to test the validator."""
    return {
        "marker": rng.choice(["Sodium", "Potassium", "Calcium", "Hemoglobin"]),
        "value": "1.0",
        "unit": "mg/dl",
    }
# ------- one panel ------------


def make_panel(rng):
    """Make a single panel for a given pattern and status, with some filler markers."""
    values = {}
    intended = {}

    for name, pattern in PATTERNS.items():
        # randomly choose a status for each pattern
        status = rng.choice(STATUSES)
        intended[name] = status

        if status == "insufficient_data":
            keep = rng.sample(pattern["requires"],
                              k=rng.randint(0, len(pattern["requires"]) - 1))
            ranges = pattern[rng.choice(["flagged", "not_flagged"])]

            for marker in keep:
                low, high = ranges[marker]
                # sample a value for the marker
                values[marker] = sample(rng, low, high)

        else:
            for marker, (low, high) in pattern[status].items():
                # sample a value for the marker
                values[marker] = sample(rng, low, high)

    for marker, (low, high) in FILLER_RANGES.items():
        if rng.random() < 0.6:  # randomly decide whether to include this filler marker
            # sample a value for the filler marker
            values[marker] = sample(rng, low, high)

    # Sanity check: make sure we have at least one marker for the pattern, otherwise the panel is invalid
    assert label(values) == intended, (label(values), values)

    # make rows for each marker
    rows = {marker: makes_row(rng, marker, value)
            for marker, value in values.items()}
    valid_values = dict(values)  # copy the values to valid_rows
    rejected_rows = []

    # Corrupt a few rows to test the validator
    if rng.random() < 0.4:  # 40% chance to corrupt a row
        marker = rng.choice(sorted(rows))  # choose a random marker to corrupt
        kind = rng.choice(CORRUPTIONS)  # choose a random corruption type
        rows[marker] = corrupt_row(rng, rows[marker], kind)
        # remove the marker from valid_values since it's corrupted
        del valid_values[marker]
        rejected_rows.append({"marker": marker, "corruption": kind})

    out_rows = list(rows.values())  # convert the rows dict to a list of rows

    # duplicate a marker that is still valid (25%)
    if valid_values and rng.random() < 0.25:
        # NOT from rows: must still be valid
        marker = rng.choice(sorted(valid_values))
        low, high = MARKERS[marker]["plausible_range"]
        out_rows.append(makes_row(rng, marker, sample(rng, low, high)))
        # both rows get rejected
        del valid_values[marker]
        rejected_rows.append({"marker": marker, "corruption": "duplicate"})

    # Sometimes add a row for a marker that isn't in the pattern, to test the validator
    if rng.random() < 0.3:  # 30% chance to add a filler marker
        out_rows.append(make_unknown_row(rng))  # add a random unknown row
        rejected_rows.append(
            {"marker": "unknown", "corruption": "not_in_pattern"})

    rng.shuffle(out_rows)  # shuffle the rows to simulate messy input
    # return the rows, the ground truth labels, and the rejected rows
    return out_rows, label(valid_values), rejected_rows


def generate(n_panels=30, seed=42):
    """Generate a number of synthetic panels, and write them to CSV files with a ground-truth JSON file."""
    rng = random.Random(
        seed)  # create a random number generator with a fixed seed for reproducibility
    # create the output directory if it doesn't exist
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ground_truth = {}  # dictionary to hold the ground truth labels for each panel
    for i in range(1, n_panels + 1):
        panel_id = f"panel_{i:03d}"  # create a panel ID like "panel_001"
        rows, labels, rejections = make_panel(rng)  # type: ignore

        # write the panel to a CSV file
        with open(OUT_DIR / f"{panel_id}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["marker", "value", "unit"])
            writer.writeheader()
            writer.writerows(rows)

        ground_truth[panel_id] = {
            "patterns": labels,  # the ground truth labels for the patterns
            "expected_rejections": rejections,  # the expected rejected rows
        }

    # write the ground truth to a JSON file
    with open(OUT_DIR / "ground_truth.json", "w", encoding="utf-8") as f:
        # ensure_ascii=False to allow special characters in the JSON file+
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    return ground_truth


if __name__ == "__main__":
    result = generate()
    print(
        f"Generated {len(result)} panels in {OUT_DIR}. Ground truth written to ground_truth.json.")
