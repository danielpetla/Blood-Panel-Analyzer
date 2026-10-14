# Blood-Panel-Analyzer

A small Python pipeline that generates messy synthetic blood panels, validates them,
asks an LLM to flag simple patterns, and scores the answers, with a focus on whether
the model abstains when data is missing.

> ⚠️ Demo project on synthetic data only. Not a medical device and not clinically validated.

## What it does

1. **Generates** synthetic, deliberately messy CSV panels (aliases, odd casing, decimal
   commas, bad or missing units, non-numeric and implausible values, duplicates, unknown
   markers) together with ground-truth labels
2. **Validates** each row (known marker, canonical unit, plausible number) and rejects
   invalid input instead of guessing
3. **Analyses** the accepted rows with an LLM that returns structured JSON: one status per
   pattern (`flagged`, `not_flagged`, `insufficient_data`) plus a short reason
4. **Evaluates** against the ground truth: accuracy per pattern, abstention precision and
   recall, false vs missed flags, a confusion matrix, and whether the validator rejected
   exactly the expected rows

Patterns (simplified demo rules): dysglycemia, atherogenic dyslipidemia, iron deficiency.

## Project structure

| File | Purpose |
|---|---|
| `markers.py` | Reference data: markers, aliases, canonical units, plausible ranges |
| `schema.py` | `LabResult` and validation: raw rows in, clean records or rejection reasons out |
| `generate.py` | Synthetic panels plus `ground_truth.json` |
| `rules.py` | Deterministic baseline that applies the threshold rules without an LLM |
| `llm.py` | Prompt and structured output from Gemini |
| `errors.py` | Shared `LLMOutputError` |
| `evaluate.py` | Runs all panels and prints the scores |
| `main.py` | Validates and analyses a single panel |

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install google-genai
```

## Run

**Without an LLM (no key needed):**

```bash
python generate.py                  # creates data/panels/ with 30 panels + ground_truth.json
python evaluate.py --mode rules     # deterministic baseline, should score 100%
```

**With Gemini:**

1. Get a free API key at https://aistudio.google.com/apikey
2. Set it in your terminal (it is read from the environment, never from the code):

   ```bash
   export GEMINI_API_KEY="your-key"      # Windows PowerShell: $env:GEMINI_API_KEY="your-key"
   ```

3. Run:

   ```bash
   python evaluate.py --mode llm
   python evaluate.py --mode llm --model <model-name> --sleep 3
   ```

The default model is set in `llm.py` (`MODEL`). Model names change over time; if you get
"model not found", pick a current one from AI Studio and pass it with `--model`.
Free tiers have rate limits and can return `503` when the model is busy. Use `--sleep` to
slow down, and `--resume` to reuse saved answers and retry only the missing panels. The run
stops after 3 API errors in a row.

To inspect one panel: `python main.py`.

## Results

Synthetic data: 30 panels, 90 pattern decisions, seed 42.

**Deterministic baseline** (`python evaluate.py --mode rules`): 90/90 correct. This is
expected by construction, because the baseline uses the same rules as the ground truth. It
shows that the generator, validator and scoring code agree with each other.

```
=== Validator ===
Rejections match expected_rejections on all 30 panels.

=== Accuracy ===
Overall: 90/90 (100.0%)
  dysglycemia                30/30 (100.0%)
  atherogenic_dyslipidemia   30/30 (100.0%)
  iron_deficiency            30/30 (100.0%)

=== Abstention (insufficient_data) ===
Precision: 43/43 (100.0%)
Recall:    43/43 (100.0%)
Guessed instead of abstaining: 0

=== Flag errors ===
False flags: 0
Missed flags: 0
```

**Gemini** (`python evaluate.py --mode llm`): a partial run (9 of 30 panels answered, the rest stopped by
API errors: 503 overloaded and 429 quota) got all 27 decisions correct.
A full run is pending. 

## Limitations

### Not a medical tool
- All data is synthetic. Don't use real patient data: free API tiers may use submitted
  content to improve the provider's products (check the current terms).
- The thresholds are simplified demo rules (for example ferritin < 30 ng/ml), not clinical
  guidelines. They ignore age, sex, pregnancy, medication, fasting state and lab-specific
  reference ranges.
- Output is a pattern flag, never a diagnosis.

### Evaluation
- **Small and single-seed:** 30 panels (90 pattern decisions) from one seed. Differences of
  a few points between models are within noise.
- **The ground truth shares its rules with the analyzer.** The thresholds are copied into
  `generate.py`, `rules.py` and the LLM prompt. The rules baseline scores 100% by
  construction, so it checks pipeline consistency, not medical correctness.
- **The prompt contains the thresholds**, so the LLM is tested on following instructions and
  abstaining correctly, not on medical knowledge.
- **Only the status is scored.** The model's written reasons are not checked, and nothing
  verifies that they cite the right values.
- **One run per model.** Even at temperature 0, hosted models can vary slightly, and results
  depend on the model version, which providers change or retire. The default model name may
  stop working.
- **Failed calls count as wrong.** An API error or malformed output scores as incorrect for
  that panel, so an outage lowers the score without saying anything about the model. A run
  that stops early scores only the panels it reached.
- **Synthetic realism is limited:** values are sampled independently (real glucose and HbA1c
  correlate), rounded to one decimal, and the messy input covers only a few corruption
  types.

### Scope
- 3 patterns and 12 markers.
- Input is a three-column CSV (`marker,value,unit`). JSON, PDFs, images and other lab
  formats are not supported.
- Only canonical units are accepted. A value in mmol/l is rejected, not converted.
- Marker names must match a known alias after lowercasing and trimming. There is no fuzzy
  matching, and aliases cover English and some German only.
- Numbers must use a decimal point or comma. Thousands separators, ranges and `<0.5`-style
  values are rejected.
- A duplicated marker rejects both rows, even if one value was correct.

### LLM step
- The model sees only the accepted rows. It cannot tell a missing marker from a rejected
  one, so a corrupted ferritin row produces `insufficient_data` without saying why.
- No automated unit tests beyond the end-to-end checks in `evaluate.py`.