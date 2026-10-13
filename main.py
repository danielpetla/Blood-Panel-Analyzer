import csv
from pathlib import Path
from schema import validate_panel
from llm import analyze, LLMOutputError

PANELS_DIR = Path(__file__).parent / "data" / "panels" # path to the folder containing the CSV files
def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f: # open the CSV file with UTF-8 encoding to handle special characters
        return list(csv.DictReader(f))

def main(): # main function to load and validate the blood panel data
    rows = load_rows(PANELS_DIR / "panel_001.csv")
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