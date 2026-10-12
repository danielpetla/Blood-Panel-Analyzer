import math
from markers import MARKERS, find_marker, units
from dataclasses import dataclass

@dataclass
class LabResult:
    marker: str
    value: float
    unit: str

def is_plausible(marker, value): # check if the value is within the plausible range for the marker
    if marker not in MARKERS:
        return False
    min_val, max_val = MARKERS[marker]["plausible_range"]
    return min_val <= value <= max_val    

def parse_value(raw): # parse the value from the raw string
    try:
        value = float(raw.strip().replace(",", ".")) # replace comma with dot for decimal conversion to avoid errors in float conversion
    except (ValueError, AttributeError):
        return None
    return value if math.isfinite(value) else None
