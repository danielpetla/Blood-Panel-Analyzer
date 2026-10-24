import math
from markers import MARKERS, find_marker, units
from dataclasses import dataclass
from collections import defaultdict


# ValidationError is a subclass of ValueError, which is raised when a raw row cannot become a valid LabResult.
class ValidationError(ValueError):
    """Raised when a raw row cannot become a valid LabResult."""


@dataclass(frozen=True)
class LabResult:
    marker: str
    value: float
    unit: str


# check if the value is within the plausible range for the marker
def is_plausible(marker, value):
    if marker not in MARKERS:
        return False
    min_val, max_val = MARKERS[marker]["plausible_range"]
    return min_val <= value <= max_val


def parse_value(raw):  # parse the value from the raw string
    try:
        # replace comma with dot for decimal conversion to avoid errors in float conversion
        value = float(raw.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None
    return value if math.isfinite(value) else None


def build_result(name, raw_value, raw_unit):  # build a LabResult from the raw inputs
    marker = find_marker(name)
    if marker is None:
        raise ValidationError(f"Unknown marker: {name!r}")
    value = parse_value(raw_value)

    if value is None:
        raise ValidationError(f"Invalid value: {raw_value!r}")

    # unit is check before range so that we can raise a more specific error if the unit is wrong
    # as a unit problem, not as an "implausible value" problem. This is important because the unit problem is a data quality problem, while the implausible value problem is a biological problem.
    unit = (raw_unit or "").strip().lower()
    canonical_unit = units(marker)

    if unit != canonical_unit:
        raise ValidationError(
            f"Unexpected unit for {marker}: {unit!r}, expected: {canonical_unit!r}"
        )

    if not is_plausible(marker, value):
        raise ValidationError(f"Value out of plausible range for {marker}: {value}")
    return LabResult(marker=marker, value=value, unit=unit)


def validate_panel(rows):  # validate a panel of lab results
    """Split raw rows into accepted LabResults and (row, reason) rejections."""
    candidates, rejected = [], []
    for row in rows:
        try:
            result = build_result(
                row.get("marker", ""), row.get("value", ""), row.get("unit", "")
            )
            candidates.append((row, result))
        except ValidationError as e:
            rejected.append((row, str(e)))

    by_marker = defaultdict(list)
    for row, result in candidates:
        by_marker[result.marker].append((row, result))

    accepted = []
    for marker, group in by_marker.items():
        if len(group) == 1:
            # only one result for this marker, accept it
            accepted.append(group[0][1])
        else:
            for row, _ in group:
                rejected.append(
                    (row, f"Duplicate marker: {marker} appears {len(group)} times")
                )
    return accepted, rejected
