import csv
from schema import validate_panel

def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def main():
    rows = load_rows("data/panel_001.csv")
    accepted, rejected = validate_panel(rows)
    
    print(f"Accepted: {len(accepted)}")
    for result in accepted:
        print(f"  {result.marker}: {result.value} {result.unit}")

    print(f"Rejected: {len(rejected)}")
    for row, reason in rejected:
        print(f"  {row} -> {reason}")

if __name__ == "__main__":
    main()