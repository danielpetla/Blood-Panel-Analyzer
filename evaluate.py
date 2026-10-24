"""Score an analyzer against ground_truth.json.

python evaluate.py --mode rules                       # free baseline, should score 100%
python evaluate.py --mode llm                         # Gemini, model from llm.py
python evaluate.py --mode llm --model gemini-3.8-flash --sleep 3
python evaluate.py --mode llm --resume                # reuse saved answers, call only missing panels
"""

import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path

from markers import find_marker
from schema import validate_panel
from rules import analyze_rules

from errors import (
    LLMOutputError,
)  # no SDK needed, so rules mode works without google-genai

PANELS_DIR = Path(__file__).parent / "data" / "panels"
STATUSES = ("flagged", "not_flagged", "insufficient_data")
PATTERNS = ("dysglycemia", "atherogenic_dyslipidemia", "iron_deficiency")
BAD_OUTPUT, API_ERROR = "bad_output", "api_error"
GUESSES = (
    "flagged",
    "not_flagged",
)  # answers that should not be given when data is missing


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rejected_markers(rejected):
    """Marker-level view: both rows of a duplicate collapse into one marker."""
    return {find_marker(r.get("marker") or "") or "unknown" for r, _ in rejected}


def get_analyzer(mode, model):
    """Return a function accepted -> {pattern: status}."""
    if mode == "rules":
        return analyze_rules
    from llm import analyze, MODEL

    chosen = model or MODEL
    print(f"Model: {chosen}")

    def run(accepted):
        result = analyze(accepted, model=chosen)
        return {p: result[p]["status"] for p in PATTERNS}

    return run


def predict_all(truth, analyzer, sleep, cache, cache_path, use_llm):
    """Validate each panel, run the analyzer, return (preds, validator_mismatches)."""
    preds, validator_bad = {}, []
    api_errors_in_a_row = 0

    for panel_id, info in truth.items():
        accepted, rejected = validate_panel(load_rows(PANELS_DIR / f"{panel_id}.csv"))

        expected = {e["marker"] for e in info["expected_rejections"]}
        got = rejected_markers(rejected)
        if got != expected:
            validator_bad.append((panel_id, expected, got))

        if panel_id in cache:  # --resume
            preds[panel_id] = cache[panel_id]
            continue

        try:
            preds[panel_id] = analyzer(accepted)
            api_errors_in_a_row = 0
        except LLMOutputError as e:
            preds[panel_id] = BAD_OUTPUT
            print(f"  {panel_id}: bad output ({e})")
        except Exception as e:  # network, quota, bad key, ...
            preds[panel_id] = API_ERROR
            api_errors_in_a_row += 1
            print(f"  {panel_id}: API error ({type(e).__name__}: {str(e)[:120]})")
            if api_errors_in_a_row >= 3:
                print("3 API errors in a row: stopping to save quota.")
                break

        if use_llm:
            cache_path.write_text(json.dumps(preds, indent=2), encoding="utf-8")
            time.sleep(sleep)
    return preds, validator_bad


def score(truth, preds):
    """Pair every (panel, pattern) with truth and prediction. Failed panels count as wrong."""
    pairs = []
    for panel_id, pred in preds.items():
        for pattern in PATTERNS:
            t = truth[panel_id]["patterns"][pattern]
            p = (
                pred[pattern] if isinstance(pred, dict) else pred
            )  # failure marker string
            pairs.append((panel_id, pattern, t, p))
    return pairs


def pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "  n/a "


def report(pairs, preds, validator_bad, n_panels):
    print("\n=== Validator ===")
    if not validator_bad:
        print(f"Rejections match expected_rejections on all {n_panels} panels.")
    for panel_id, exp, got in validator_bad:
        print(f"  MISMATCH {panel_id}: expected {sorted(exp)} got {sorted(got)}")

    failed = Counter(p for p in preds.values() if isinstance(p, str))
    print("\n=== Analyzer run ===")
    print(f"Panels scored: {len(preds)}/{n_panels}")
    print(f"Bad output: {failed[BAD_OUTPUT]}   API errors: {failed[API_ERROR]}")

    print("\n=== Accuracy ===")
    total_ok = sum(t == p for _, _, t, p in pairs)
    print(f"Overall: {total_ok}/{len(pairs)} ({pct(total_ok, len(pairs))})")
    for pattern in PATTERNS:
        sub = [(t, p) for _, pat, t, p in pairs if pat == pattern]
        ok = sum(t == p for t, p in sub)
        print(f"  {pattern:26s} {ok}/{len(sub)} ({pct(ok, len(sub))})")

    print("\n=== Abstention (insufficient_data) ===")
    tp = sum(
        t == "insufficient_data" and p == "insufficient_data" for _, _, t, p in pairs
    )
    pred_pos = sum(p == "insufficient_data" for _, _, _, p in pairs)
    true_pos = sum(t == "insufficient_data" for _, _, t, _ in pairs)
    print(
        f"Precision: {tp}/{pred_pos} ({pct(tp, pred_pos)})   (when it abstains, is it right?)"
    )
    print(
        f"Recall:    {tp}/{true_pos} ({pct(tp, true_pos)})   (when data is missing, does it abstain?)"
    )
    guessed = sum(t == "insufficient_data" and p in GUESSES for _, _, t, p in pairs)
    print(f"Guessed instead of abstaining: {guessed}")

    print("\n=== Flag errors ===")
    false_flag = [
        (i, pat) for i, pat, t, p in pairs if p == "flagged" and t != "flagged"
    ]
    missed = [(i, pat) for i, pat, t, p in pairs if t == "flagged" and p != "flagged"]
    print(f"False flags (said flagged, truth not): {len(false_flag)}")
    print(f"Missed flags (truth flagged, said otherwise): {len(missed)}")

    print("\n=== Confusion matrix (rows = truth, columns = prediction) ===")
    cols = STATUSES + (BAD_OUTPUT, API_ERROR)
    print(f"{'':20s}" + "".join(f"{c[:12]:>14s}" for c in cols))
    for t in STATUSES:
        row = Counter(p for _, _, tt, p in pairs if tt == t)
        print(f"{t:20s}" + "".join(f"{row[c]:>14d}" for c in cols))

    wrong = [(i, pat, t, p) for i, pat, t, p in pairs if t != p]
    if wrong:
        print(f"\n=== Wrong answers (first 15 of {len(wrong)}) ===")
        for i, pat, t, p in wrong[:15]:
            print(f"  {i} {pat}: truth={t} got={p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("rules", "llm"), default="rules")
    ap.add_argument("--model", default=None)
    ap.add_argument(
        "--sleep", type=float, default=2.0, help="seconds between LLM calls"
    )
    ap.add_argument("--resume", action="store_true", help="reuse saved LLM answers")
    args = ap.parse_args()

    truth = json.loads((PANELS_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    cache_path = Path(__file__).parent / "results_llm.json"
    cache = {}
    if args.resume and cache_path.exists():
        cache = {
            k: v
            for k, v in json.loads(cache_path.read_text()).items()
            if isinstance(v, dict)
        }  # redo panels that failed last time
        print(f"Resuming with {len(cache)} saved panels")

    analyzer = get_analyzer(args.mode, args.model)
    preds, validator_bad = predict_all(
        truth, analyzer, args.sleep, cache, cache_path, args.mode == "llm"
    )
    report(score(truth, preds), preds, validator_bad, len(truth))


if __name__ == "__main__":
    main()
