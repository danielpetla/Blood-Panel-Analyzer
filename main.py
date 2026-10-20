import csv
import sys
from pathlib import Path
from schema import validate_panel
from llm import analyze
from errors import LLMOutputError

# path to the folder containing the CSV files
PANELS_DIR = Path(__file__).parent / "data" / "panels"


def load_rows(path):
    # open the CSV file with UTF-8 encoding to handle special characters
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():  # main function to load and validate the blood panel data
    panel_id = sys.argv[1] if len(sys.argv) > 1 else "panel_001"
    rows = load_rows(PANELS_DIR / f"{panel_id}.csv")
    accepted, rejected = validate_panel(rows)

    print(f"Accepted: {len(accepted)}")
    for result in accepted:
        print(f"  {result.marker}: {result.value} {result.unit}")

    print(f"Rejected: {len(rejected)}")
    for row, reason in rejected:
        print(f"  {row} -> {reason}")

    try:
        result = analyze(accepted)
    except LLMOutputError as e:
        print(f"LLM output invalid: {e}")
        return
    for name, r in result.items():
        print(f"{name}: {r['status']} ({r['reason']})")


if __name__ == "__main__":
    main()
